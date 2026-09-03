from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pressure_room import db
from pressure_room.ui import inject_css, brand, page_header, card
from pressure_room.analysis import PRESSURE_MOVES, scene_health, story_mri, writers_room_questions

st.set_page_config(page_title="Pressure Room", page_icon="🎬", layout="wide")
inject_css()
db.init_db()

def safe_rerun():
    st.rerun()

def choose_project():
    projects = db.get_projects()
    labels = {p["id"]: p["title"] for p in projects}
    selected = st.sidebar.selectbox("Story", list(labels), format_func=lambda x: labels[x])
    return next(p for p in projects if p["id"] == selected)

def choose_episode(project_id: str, label="Episode"):
    eps = db.get_episodes(project_id)
    if not eps:
        return None
    labels = {e["id"]: f"E{e['number']} · {e['title']}" for e in eps}
    selected = st.selectbox(label, list(labels), format_func=lambda x: labels[x])
    return next(e for e in eps if e["id"] == selected)

def form_character(project):
    with st.form("new_character", clear_on_submit=True):
        a,b = st.columns(2)
        name = a.text_input("Name")
        role = b.text_input("Role", placeholder="Protagonist")
        want = st.text_area("Want — what are they actively trying to get?")
        need = st.text_area("Need — what truth do they resist?")
        belief = st.text_area("Core belief")
        boundary = st.text_area("Moral boundary — what will they NOT do?")
        fear = st.text_area("Fear")
        temptation = st.text_area("Temptation")
        score = st.slider("Current moral compromise", 0, 10, 0)
        submitted = st.form_submit_button("Add character", use_container_width=True)
        if submitted and name.strip():
            ts = db.now_iso()
            db.insert("characters", {
                "project_id": project["id"], "name": name.strip(), "role": role.strip(),
                "want": want.strip(), "need": need.strip(), "core_belief": belief.strip(),
                "moral_boundary": boundary.strip(), "fear": fear.strip(), "temptation": temptation.strip(),
                "moral_score": score, "created_at": ts, "updated_at": ts
            })
            safe_rerun()

def causal_dot(scenes, links):
    ids = {s["id"]: s for s in scenes}
    lines = [
        "digraph G {",
        'rankdir=LR; bgcolor="transparent";',
        'node [shape=box style="rounded,filled" fillcolor="#151920" color="#3A424D" fontcolor="#F3F1EA" fontname="Arial" margin="0.16,0.10"];',
        'edge [fontname="Arial" fontsize=10 penwidth=1.4];'
    ]
    for s in scenes:
        label = f"S{s['scene_no']}\\n{(s['slugline'] or 'Untitled scene')[:34]}"
        lines.append(f'"{s["id"]}" [label="{label}"];')
    for l in links:
        color = "#E6B85C" if l["relation"] == "THEREFORE" else "#E76F51"
        lines.append(f'"{l["from_scene_id"]}" -> "{l["to_scene_id"]}" [label="{l["relation"]}" color="{color}" fontcolor="{color}"];')
    lines.append("}")
    return "\n".join(lines)

# Sidebar
with st.sidebar:
    brand()
    st.markdown("---")
    nav = st.radio(
        "Workspace",
        ["Home", "Story Bible", "Causal Map", "Scene Builder", "Bill Ledger", "Pressure Lab", "Story MRI", "Writers’ Room"],
        label_visibility="collapsed"
    )
    st.markdown("---")

project = choose_project()

# Create story in sidebar
with st.sidebar.expander("＋ New story"):
    with st.form("new_project", clear_on_submit=True):
        title = st.text_input("Title")
        premise = st.text_area("Premise")
        theme = st.text_input("Theme / dramatic question")
        if st.form_submit_button("Create story", use_container_width=True) and title.strip():
            ts = db.now_iso()
            pid = db.insert("projects", {"title":title.strip(),"premise":premise.strip(),"theme":theme.strip(),"created_at":ts,"updated_at":ts})
            db.insert("branches", {"project_id":pid,"name":"Main","is_main":1,"created_at":ts})
            safe_rerun()

characters = db.get_characters(project["id"])
episodes = db.get_episodes(project["id"])
bills = db.get_bills(project["id"])

# HOME
if nav == "Home":
    page_header("Story pressure dashboard", project["title"], project.get("premise",""))
    active_bills = [b for b in bills if b["status"] in ("Outstanding","Escalating")]
    all_scenes = []
    for ep in episodes:
        all_scenes.extend(db.get_scenes(ep["id"]))
    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(card("Characters", str(len(characters)), "Moral spines in play"), unsafe_allow_html=True)
    c2.markdown(card("Episodes", str(len(episodes)), "Main branch + experiments"), unsafe_allow_html=True)
    c3.markdown(card("Scenes", str(len(all_scenes)), "Choices under pressure"), unsafe_allow_html=True)
    c4.markdown(card("Unpaid bills", str(len(active_bills)), "Consequences still alive"), unsafe_allow_html=True)

    st.markdown("### The engine")
    st.markdown(
        '<div class="pr-quote"><b>Character wants something → makes a choice → consequence → pressure narrows options → a harder choice → the bill comes due → the boundary moves.</b></div>',
        unsafe_allow_html=True
    )
    a,b = st.columns([1.25,1])
    with a:
        st.markdown("### Current moral spines")
        if characters:
            for c in characters:
                st.markdown(f"""
                <div class="pr-card" style="margin-bottom:.65rem">
                  <div class="pr-card-title">{c.get('role') or 'Character'}</div>
                  <div style="font-size:1.15rem;font-weight:800">{c['name']}</div>
                  <div class="pr-sub" style="margin-top:.35rem"><b>Wants:</b> {c.get('want') or '—'}</div>
                  <div class="pr-sub"><b>Won’t do:</b> {c.get('moral_boundary') or '—'}</div>
                  <div style="margin-top:.55rem"><span class="pr-pill">Compromise {c['moral_score']}/10</span></div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Add your first character in Story Bible.")
    with b:
        st.markdown("### Bills demanding attention")
        if active_bills:
            for bill in active_bills[:5]:
                st.markdown(f"""
                <div class="pr-card" style="margin-bottom:.65rem">
                  <div class="pr-card-title">{bill['status']}</div>
                  <div style="font-weight:800">{bill['title']}</div>
                  <div class="pr-sub" style="margin-top:.3rem">{bill.get('external_cost') or ''}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("No outstanding bills. Either the story is very clean… or not enough damage has been done yet.")

# STORY BIBLE
elif nav == "Story Bible":
    page_header("Character architecture", "Story Bible", "Define what each character wants, believes, fears, and refuses to do.")
    with st.expander("Story premise & theme", expanded=True):
        with st.form("edit_project"):
            title = st.text_input("Title", project["title"])
            premise = st.text_area("Premise", project.get("premise",""), height=100)
            theme = st.text_input("Theme / dramatic question", project.get("theme",""))
            if st.form_submit_button("Save story"):
                db.update("projects", project["id"], {"title":title,"premise":premise,"theme":theme})
                safe_rerun()

    st.markdown("### Characters")
    if characters:
        cols = st.columns(2)
        for i,c in enumerate(characters):
            with cols[i % 2]:
                with st.expander(f"{c['name']} · {c.get('role') or 'Character'}", expanded=True):
                    st.markdown(f"**Want**  \n{c.get('want') or '—'}")
                    st.markdown(f"**Need**  \n{c.get('need') or '—'}")
                    st.markdown(f"**Core belief**  \n{c.get('core_belief') or '—'}")
                    st.markdown(f"**Moral boundary**  \n{c.get('moral_boundary') or '—'}")
                    st.markdown(f"**Fear**  \n{c.get('fear') or '—'}")
                    st.markdown(f"**Temptation**  \n{c.get('temptation') or '—'}")
                    st.progress(c["moral_score"]/10, text=f"Moral compromise · {c['moral_score']}/10")
    st.markdown("### Add character")
    form_character(project)

    st.markdown("### Episodes")
    for e in episodes:
        st.markdown(f"**E{e['number']} · {e['title']}**  \n<span class='pr-muted'>{e.get('logline') or ''}</span>", unsafe_allow_html=True)
    with st.expander("＋ Add episode"):
        with st.form("new_episode", clear_on_submit=True):
            num = st.number_input("Episode number", 1, 999, value=(max([e["number"] for e in episodes], default=0)+1))
            title = st.text_input("Episode title")
            logline = st.text_area("Logline")
            if st.form_submit_button("Add episode", use_container_width=True) and title.strip():
                main = db.one("SELECT id FROM branches WHERE project_id=? AND is_main=1 LIMIT 1", [project["id"]])
                ts=db.now_iso()
                db.insert("episodes", {"project_id":project["id"],"branch_id":main["id"],"number":int(num),"title":title.strip(),"logline":logline.strip(),"status":"Outline","created_at":ts,"updated_at":ts})
                safe_rerun()

# CAUSAL MAP
elif nav == "Causal Map":
    page_header("Therefore / But", "Causal Map", "Plot should feel caused, not merely arranged.")
    ep = choose_episode(project["id"])
    if not ep:
        st.warning("Create an episode first.")
    else:
        scenes = db.get_scenes(ep["id"])
        links = db.get_links(ep["id"])
        if scenes:
            st.graphviz_chart(causal_dot(scenes, links), use_container_width=True)
        else:
            st.info("Add scenes in Scene Builder.")
        st.markdown("### Connect scenes")
        if len(scenes) >= 2:
            labels={s["id"]:f"S{s['scene_no']} · {s['slugline'] or 'Untitled'}" for s in scenes}
            with st.form("new_link", clear_on_submit=True):
                c1,c2,c3 = st.columns([1,0.8,1])
                src=c1.selectbox("From", list(labels), format_func=lambda x:labels[x])
                rel=c2.selectbox("Relationship", ["THEREFORE","BUT"])
                dst=c3.selectbox("To", list(labels), index=min(1,len(labels)-1), format_func=lambda x:labels[x])
                note=st.text_input("Why does this follow?")
                if st.form_submit_button("Connect", use_container_width=True):
                    if src == dst:
                        st.error("A scene cannot cause itself.")
                    else:
                        try:
                            db.insert("causal_links", {"episode_id":ep["id"],"from_scene_id":src,"relation":rel,"to_scene_id":dst,"note":note,"created_at":db.now_iso()})
                            safe_rerun()
                        except Exception:
                            st.warning("That connection already exists.")
        if links:
            st.markdown("### Existing links")
            for l in links:
                st.markdown(f"**S{l['from_no']}** → **{l['relation']}** → **S{l['to_no']}**  \n{l.get('note') or ''}")

# SCENE BUILDER
elif nav == "Scene Builder":
    page_header("Action → pressure → choice → change", "Scene Builder", "Build scenes around what changes, not around what gets discussed.")
    ep = choose_episode(project["id"])
    if not ep:
        st.warning("Create an episode first.")
    else:
        scenes = db.get_scenes(ep["id"])
        char_labels={c["id"]:c["name"] for c in characters}
        st.markdown("### Add scene")
        with st.form("new_scene", clear_on_submit=True):
            r1c1,r1c2,r1c3 = st.columns([0.35,1.2,0.8])
            scene_no = r1c1.number_input("Scene", 1, 999, value=max([s["scene_no"] for s in scenes], default=0)+1)
            slugline = r1c2.text_input("Slugline", placeholder="INT. KITCHEN — NIGHT")
            pov = r1c3.selectbox("POV / pressure character", [""]+list(char_labels), format_func=lambda x: "—" if x=="" else char_labels[x])
            opening = st.text_area("Opening behavior / image", placeholder="What are we watching before anyone explains the scene?")
            c1,c2 = st.columns(2)
            want = c1.text_area("What do they want in this scene?")
            obstacle = c2.text_area("Why can’t they simply get it?")
            c3,c4 = st.columns(2)
            tactic = c3.text_area("Tactic")
            pressure = c4.text_area("Pressure — what narrows their options?")
            choice = st.text_area("Choice — what do they decide or commit to?")
            c5,c6 = st.columns(2)
            start = c5.text_area("Starting state")
            end = c6.text_area("Ending state")
            cut_on = st.text_input("Cut on…", placeholder="A choice, reveal, changed behavior, irreversible action")
            moral_delta = st.slider("Moral compromise added by this scene", -2, 3, 0)
            notes = st.text_area("Notes")
            if st.form_submit_button("Add scene", use_container_width=True):
                ts=db.now_iso()
                db.insert("scenes", {
                    "episode_id":ep["id"],"scene_no":int(scene_no),"slugline":slugline.strip(),"pov_character_id":pov or None,
                    "opening_behavior":opening.strip(),"scene_want":want.strip(),"obstacle":obstacle.strip(),"tactic":tactic.strip(),
                    "pressure":pressure.strip(),"choice":choice.strip(),"start_state":start.strip(),"end_state":end.strip(),
                    "cut_on":cut_on.strip(),"notes":notes.strip(),"moral_delta":int(moral_delta),"created_at":ts,"updated_at":ts
                })
                safe_rerun()

        st.markdown("### Episode scenes")
        for s in scenes:
            health=scene_health(s)
            with st.expander(f"S{s['scene_no']} · {s['slugline'] or 'Untitled scene'}", expanded=False):
                a,b,c = st.columns(3)
                a.markdown(f"**WANT**  \n{s.get('scene_want') or '—'}")
                b.markdown(f"**PRESSURE**  \n{s.get('pressure') or '—'}")
                c.markdown(f"**CHOICE**  \n{s.get('choice') or '—'}")
                st.markdown(f"**CHANGE** · {s.get('start_state') or '—'} → {s.get('end_state') or '—'}")
                st.markdown(f"**CUT ON** · {s.get('cut_on') or '—'}")
                if health:
                    st.warning(" · ".join(health))
                else:
                    st.success("This scene records pressure, choice, transformation, and an exit beat.")

# BILL LEDGER
elif nav == "Bill Ledger":
    page_header("Cause & cost", "Bill Ledger", "Every choice can create an external bill and an internal moral cost.")
    st.markdown("### Add a bill")
    char_labels={c["id"]:c["name"] for c in characters}
    ep_labels={e["id"]:f"E{e['number']} · {e['title']}" for e in episodes}
    with st.form("new_bill", clear_on_submit=True):
        title=st.text_input("Bill", placeholder="The lie to the clerk")
        c1,c2=st.columns(2)
        external=c1.text_area("External bill — what did this choice cause in the world?")
        moral=c2.text_area("Moral cost — what did making this choice do to the character?")
        c3,c4=st.columns(2)
        char_id=c3.selectbox("Character", [""]+list(char_labels), format_func=lambda x:"—" if not x else char_labels[x])
        ep_id=c4.selectbox("Episode", [""]+list(ep_labels), format_func=lambda x:"—" if not x else ep_labels[x])
        status=st.selectbox("Status", ["Outstanding","Escalating","Paid","Abandoned"])
        if st.form_submit_button("Record bill", use_container_width=True) and title.strip():
            ts=db.now_iso()
            db.insert("bills", {"project_id":project["id"],"episode_id":ep_id or None,"scene_id":None,"character_id":char_id or None,
                                "title":title.strip(),"external_cost":external.strip(),"moral_cost":moral.strip(),"status":status,
                                "payoff_scene_id":None,"created_at":ts,"updated_at":ts})
            safe_rerun()

    st.markdown("### Ledger")
    if bills:
        for bill in bills:
            icon={"Outstanding":"○","Escalating":"▲","Paid":"✓","Abandoned":"–"}[bill["status"]]
            with st.expander(f"{icon} {bill['title']} · {bill['status']}", expanded=bill["status"] in ("Outstanding","Escalating")):
                st.markdown(f"**External bill**  \n{bill.get('external_cost') or '—'}")
                st.markdown(f"**Moral cost**  \n{bill.get('moral_cost') or '—'}")
                st.caption("Character: " + (bill.get("character_name") or "—"))
                new_status=st.selectbox("Update status", ["Outstanding","Escalating","Paid","Abandoned"],
                                        index=["Outstanding","Escalating","Paid","Abandoned"].index(bill["status"]), key=f"bs_{bill['id']}")
                if st.button("Save status", key=f"save_{bill['id']}"):
                    db.update("bills", bill["id"], {"status":new_status})
                    safe_rerun()
    else:
        st.info("No bills yet. Choices without consequences are suspicious.")

# PRESSURE LAB
elif nav == "Pressure Lab":
    page_header("Make the solution stop working", "Pressure Lab", "Pressure is not louder conflict. It is shrinking the character’s safe option-space.")
    st.markdown('<div class="pr-quote">Ask: <b>What is the character currently relying on—and how can the story remove it?</b></div>', unsafe_allow_html=True)
    cols=st.columns(2)
    for i,(name,desc) in enumerate(PRESSURE_MOVES.items()):
        with cols[i%2]:
            st.markdown(f"""
            <div class="pr-card" style="margin-bottom:.7rem">
              <div class="pr-card-title">Pressure move</div>
              <div style="font-size:1.08rem;font-weight:800">{name}</div>
              <div class="pr-sub" style="margin-top:.3rem">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("### Pressure test a character")
    if characters:
        labels={c["id"]:c["name"] for c in characters}
        cid=st.selectbox("Character", list(labels), format_func=lambda x:labels[x])
        c=next(x for x in characters if x["id"]==cid)
        a,b=st.columns(2)
        a.markdown(f"**Current want**  \n{c.get('want') or '—'}")
        b.markdown(f"**Boundary**  \n{c.get('moral_boundary') or '—'}")
        st.markdown(f"""
        <div class="pr-card">
          <div class="pr-card-title">Pressure question</div>
          <div class="pr-card-value" style="font-size:1.15rem">
          What combination of necessity, deadline, collateral damage, and prior consequence would make {c['name']} consider crossing that boundary?
          </div>
        </div>
        """, unsafe_allow_html=True)

# STORY MRI
elif nav == "Story MRI":
    page_header("See the hidden shape", "Story MRI", "A diagnostic view of pressure, moral compromise, and shrinking option-space.")
    ep=choose_episode(project["id"])
    if not ep:
        st.warning("Create an episode first.")
    else:
        scenes=db.get_scenes(ep["id"])
        mri=story_mri(scenes,bills)
        if not mri:
            st.info("Add scenes to generate the MRI.")
        else:
            df=pd.DataFrame(mri)
            fig=go.Figure()
            fig.add_trace(go.Scatter(x=df["scene"],y=df["pressure"],mode="lines+markers",name="Pressure"))
            fig.add_trace(go.Scatter(x=df["scene"],y=df["moral_compromise"],mode="lines+markers",name="Moral compromise"))
            fig.add_trace(go.Scatter(x=df["scene"],y=df["option_space"],mode="lines+markers",name="Option-space"))
            fig.update_layout(height=430, margin=dict(l=20,r=20,t=20,b=20), yaxis=dict(range=[0,10], title="0–10"),
                              legend=dict(orientation="h", y=1.1), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
            c1,c2,c3=st.columns(3)
            c1.metric("Peak pressure", int(df["pressure"].max()))
            c2.metric("End moral compromise", int(df["moral_compromise"].iloc[-1]))
            c3.metric("Remaining option-space", int(df["option_space"].iloc[-1]))
            st.caption("These are structural diagnostics, not quality scores. They are meant to provoke questions, not grade the writing.")

# WRITERS' ROOM
elif nav == "Writers’ Room":
    page_header("Optional, not the author", "Writers’ Room", "A supplementary interrogation tool. Pressure Room works completely without AI.")
    st.markdown("""
    <div class="pr-quote">
    <b>Design principle:</b> the assistant should interrogate the writers’ room, not replace it.
    It asks the annoying structural questions that expose easy exits, unpaid bills, unearned turns, and choices that do not yet feel inevitable.
    </div>
    """, unsafe_allow_html=True)
    ep=choose_episode(project["id"])
    scenes=db.get_scenes(ep["id"]) if ep else []
    character=None
    if characters:
        labels={c["id"]:c["name"] for c in characters}
        cid=st.selectbox("Put a character in the chair", list(labels), format_func=lambda x:labels[x])
        character=next(c for c in characters if c["id"]==cid)
    qs=writers_room_questions(project,character,scenes,bills)
    st.markdown("### Questions for the room")
    for i,q in enumerate(qs,1):
        st.markdown(f"""
        <div class="pr-card" style="margin-bottom:.65rem">
          <div class="pr-card-title">Question {i:02d}</div>
          <div style="font-size:1.06rem;font-weight:700;margin-top:.25rem">{q}</div>
        </div>
        """, unsafe_allow_html=True)
    st.info("V1 deliberately keeps this rule-based and optional. A future model-backed assistant can use the same story database without becoming a dependency.")

st.markdown("<div class='pr-divider'></div><div class='pr-sub'>Pressure Room · V0.1 · Writers, under pressure.</div>", unsafe_allow_html=True)
