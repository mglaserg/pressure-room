Pressure Room legal pages

Copy/extract this archive into the root of the pressure-room repository, allowing
frontend/app/layout.js and frontend/app/globals.css to be overwritten.

Then run:
  git diff --check
  git status
  git add frontend/app/privacy frontend/app/terms frontend/styles/legal.css frontend/app/globals.css frontend/app/layout.js
  git commit -m "Add public privacy policy and terms"
  git push

After Amplify deploys:
  https://main.d23277cgmbx1g0.amplifyapp.com/privacy
  https://main.d23277cgmbx1g0.amplifyapp.com/terms
