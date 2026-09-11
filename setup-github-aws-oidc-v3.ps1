# Pressure Room GitHub Actions AWS OIDC setup - v3
# Windows PowerShell 5.1 compatible
#
# Run:
#   Set-ExecutionPolicy -Scope Process Bypass
#   .\setup-github-aws-oidc-fixed.ps1
#
# This script:
#   1. Detects your AWS account.
#   2. Creates/reuses the GitHub AWS OIDC provider.
#   3. Creates/updates PressureRoomGitHubDeploy.
#   4. Adds ECR push and ECS Express deployment permissions.
#   5. Prints the AWS_DEPLOY_ROLE_ARN value to add in GitHub.

$ErrorActionPreference = 'Stop'

$Region = 'us-east-2'
$RoleName = 'PressureRoomGitHubDeploy'
$PolicyName = 'PressureRoomDeploy'
$EcrRepository = 'pressure-room-api'

$GitHubOwner = 'mglaserg'
$GitHubOwnerId = '13452733'
$GitHubRepo = 'pressure-room'
$GitHubRepoId = '1356084446'
$GitHubEnvironment = 'production'

function Assert-AwsSuccess {
    param(
        [string]$Message
    )

    if ($LASTEXITCODE -ne 0) {
        throw $Message
    }
}

function Write-JsonFile {
    param(
        [string]$Path,
        [object]$Object
    )

    # AWS CLI policy documents must be clean UTF-8 JSON. Windows PowerShell
    # 5.1's Set-Content -Encoding UTF8 writes a BOM, so explicitly write
    # UTF-8 without BOM here.
    $Json = $Object | ConvertTo-Json -Depth 20
    $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Json, $Utf8NoBom)
}

Write-Host ''
Write-Host 'Pressure Room GitHub/AWS OIDC setup' -ForegroundColor Cyan
Write-Host '===================================' -ForegroundColor Cyan
Write-Host ''

Write-Host '[1/6] Checking local AWS credentials...'

$AccountId = aws sts get-caller-identity --query Account --output text
Assert-AwsSuccess 'Your local AWS CLI credentials are not working.'
$AccountId = $AccountId.Trim()

$CallerArn = aws sts get-caller-identity --query Arn --output text
Assert-AwsSuccess 'Could not read the current AWS caller ARN.'
$CallerArn = $CallerArn.Trim()

if ([string]::IsNullOrWhiteSpace($AccountId)) {
    throw 'AWS returned an empty account ID.'
}

Write-Host ('      Account: ' + $AccountId)
Write-Host ('      Caller:  ' + $CallerArn)

$ProviderArn = 'arn:aws:iam::' + $AccountId + ':oidc-provider/token.actions.githubusercontent.com'

Write-Host '[2/6] Checking GitHub OIDC provider...'

$ExistingProviderArn = aws iam list-open-id-connect-providers --query "OpenIDConnectProviderList[?Arn=='$ProviderArn'].Arn | [0]" --output text
Assert-AwsSuccess 'Failed to list AWS OIDC providers.'
$ProviderExists = (-not [string]::IsNullOrWhiteSpace($ExistingProviderArn)) -and ($ExistingProviderArn.Trim() -ne 'None')

if (-not $ProviderExists) {
    Write-Host '      Creating GitHub OIDC provider...'

    aws iam create-open-id-connect-provider --url 'https://token.actions.githubusercontent.com' --client-id-list 'sts.amazonaws.com' --output json | Out-Null
    Assert-AwsSuccess 'Failed to create the GitHub OIDC provider.'
}
else {
    Write-Host '      Provider already exists.'
}

Write-Host '[3/6] Building trust policy...'

$ImmutableSubject = 'repo:' + $GitHubOwner + '@' + $GitHubOwnerId + '/' + $GitHubRepo + '@' + $GitHubRepoId + ':environment:' + $GitHubEnvironment
$LegacySubject = 'repo:' + $GitHubOwner + '/' + $GitHubRepo + ':environment:' + $GitHubEnvironment

$TrustCondition = @{}
$TrustCondition['token.actions.githubusercontent.com:aud'] = 'sts.amazonaws.com'
$TrustCondition['token.actions.githubusercontent.com:sub'] = @(
    $ImmutableSubject,
    $LegacySubject
)

$TrustPolicy = @{
    Version = '2012-10-17'
    Statement = @(
        @{
            Effect = 'Allow'
            Principal = @{
                Federated = $ProviderArn
            }
            Action = 'sts:AssumeRoleWithWebIdentity'
            Condition = @{
                StringEquals = $TrustCondition
            }
        }
    )
}

$TrustPath = Join-Path $env:TEMP 'pressure-room-github-trust.json'
Write-JsonFile -Path $TrustPath -Object $TrustPolicy

Write-Host ('      Immutable subject: ' + $ImmutableSubject)

Write-Host '[4/6] Creating or updating deploy role...'

$ExistingRoleName = aws iam list-roles --query "Roles[?RoleName=='$RoleName'].RoleName | [0]" --output text
Assert-AwsSuccess 'Failed to list IAM roles.'
$RoleExists = (-not [string]::IsNullOrWhiteSpace($ExistingRoleName)) -and ($ExistingRoleName.Trim() -ne 'None')

if ($RoleExists) {
    Write-Host '      Updating existing role trust policy...'
    & aws iam update-assume-role-policy --role-name $RoleName --policy-document ('file://' + $TrustPath)
    if ($LASTEXITCODE -ne 0) {
        throw 'AWS rejected the deploy-role trust policy. The AWS error is printed immediately above.'
    }
    Write-Host '      Existing role updated.'
}
else {
    Write-Host '      Creating role...'
    & aws iam create-role --role-name $RoleName --description 'GitHub Actions OIDC deploy role for Pressure Room' --assume-role-policy-document ('file://' + $TrustPath) --output json
    if ($LASTEXITCODE -ne 0) {
        throw 'AWS rejected creation of the deploy role. The AWS error is printed immediately above.'
    }
    Write-Host '      Role created.'
}

Write-Host '[5/6] Adding ECR and ECS Express deployment permissions...'

$EcrArn = 'arn:aws:ecr:' + $Region + ':' + $AccountId + ':repository/' + $EcrRepository

$DeployPolicy = @{
    Version = '2012-10-17'
    Statement = @(
        @{
            Sid = 'EcrAuthorization'
            Effect = 'Allow'
            Action = @(
                'ecr:GetAuthorizationToken'
            )
            Resource = '*'
        },
        @{
            Sid = 'PressureRoomEcrPush'
            Effect = 'Allow'
            Action = @(
                'ecr:BatchCheckLayerAvailability',
                'ecr:GetDownloadUrlForLayer',
                'ecr:BatchGetImage',
                'ecr:InitiateLayerUpload',
                'ecr:UploadLayerPart',
                'ecr:CompleteLayerUpload',
                'ecr:PutImage'
            )
            Resource = $EcrArn
        },
        @{
            Sid = 'EcsExpressDeploy'
            Effect = 'Allow'
            Action = @(
                'ecs:CreateCluster',
                'ecs:RegisterTaskDefinition',
                'ecs:CreateExpressGatewayService',
                'ecs:UpdateExpressGatewayService',
                'ecs:DescribeExpressGatewayService',
                'ecs:DescribeClusters',
                'ecs:DescribeServices',
                'ecs:ListServiceDeployments',
                'ecs:DescribeServiceDeployments',
                'ecs:TagResource',
                'ecs:UntagResource',
                'iam:PassRole'
            )
            Resource = '*'
        }
    )
}

$PolicyPath = Join-Path $env:TEMP 'pressure-room-github-policy.json'
Write-JsonFile -Path $PolicyPath -Object $DeployPolicy

& aws iam put-role-policy --role-name $RoleName --policy-name $PolicyName --policy-document ('file://' + $PolicyPath)
if ($LASTEXITCODE -ne 0) {
    throw 'AWS rejected the deploy permissions policy. The AWS error is printed immediately above.'
}

Write-Host '[6/6] Resolving deploy role ARN...'

$RoleArn = aws iam get-role --role-name $RoleName --query Role.Arn --output text
Assert-AwsSuccess 'Could not retrieve the deploy role ARN.'
$RoleArn = $RoleArn.Trim()

Remove-Item $TrustPath -Force -ErrorAction SilentlyContinue
Remove-Item $PolicyPath -Force -ErrorAction SilentlyContinue

Write-Host ''
Write-Host 'SUCCESS' -ForegroundColor Green
Write-Host '=======' -ForegroundColor Green
Write-Host ''
Write-Host 'Add this GitHub environment variable:'
Write-Host ''
Write-Host '  GitHub repository: mglaserg/pressure-room'
Write-Host '  Settings -> Environments -> production'
Write-Host '  Environment variables -> Add variable'
Write-Host ''
Write-Host '  Name:  AWS_DEPLOY_ROLE_ARN'
Write-Host ('  Value: ' + $RoleArn) -ForegroundColor Yellow
Write-Host ''
Write-Host 'Then re-run the failed Deploy Pressure Room backend workflow.'
Write-Host ''
