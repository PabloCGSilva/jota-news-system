# GitHub Actions Setup Guide - Step by Step

## What is GitHub Actions?

GitHub Actions is a CI/CD platform built into GitHub that automatically runs code when certain events happen (like pushing code, creating pull requests, etc.). It's **free for public repositories** and has generous limits for private ones.

## Step 1: Push Your Code to GitHub

### 1.1 Create a GitHub Repository

1. Go to [github.com](https://github.com)
2. Click "New repository" (green button)
3. Name it: `jota-news-system`
4. Make it **Public** (for free GitHub Actions)
5. Click "Create repository"

### 1.2 Push Your Local Code

```bash
# In your project directory
cd /mnt/c/Users/pablo/JOTA/jota-news-system

# Initialize git (if not already done)
git init

# Add GitHub remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/jota-news-system.git

# Add all files
git add .

# Commit
git commit -m "Initial commit: JOTA News System with CI/CD"

# Push to GitHub
git push -u origin main
```

## Step 2: GitHub Actions Will Start Automatically

✨ **That's it!** GitHub Actions will automatically detect the `.github/workflows/` files and start running.

### What Happens Next:

1. **Automatic Trigger**: As soon as you push, GitHub will see the workflow files
2. **Pipeline Starts**: The CI/CD pipeline begins running
3. **Real-time Monitoring**: You can watch it in the "Actions" tab

## Step 3: Monitor Your First Run

### 3.1 View Actions Tab

1. Go to your GitHub repository
2. Click the **"Actions"** tab (next to "Code", "Issues", etc.)
3. You'll see your workflows running:
   - `JOTA News System CI/CD`
   - `Pull Request Checks` (when you create PRs)

### 3.2 Watch the Pipeline

Click on any running workflow to see:
- ✅ **Green checkmarks**: Successful steps
- ❌ **Red X's**: Failed steps  
- 🟡 **Yellow circles**: Running steps
- 📋 **Logs**: Detailed output for each step

### 3.3 What You'll See Running

```
✅ quality-checks
  ├── ✅ Code formatting check (Black)
  ├── ✅ Import sorting check (isort)  
  ├── ✅ Linting (flake8)
  └── ✅ Security check (Bandit)

✅ test
  ├── ✅ Setup Python
  ├── ✅ Install dependencies
  ├── ✅ Run tests with coverage
  └── ✅ Upload coverage

✅ build
  ├── ✅ Build Docker image
  └── ✅ Cache layers

✅ integration-test
  ├── ✅ Start services  
  ├── ✅ Test API endpoints
  └── ✅ Cleanup
```

## Step 4: Understanding the Workflow Files

### 4.1 Main Workflow (`.github/workflows/ci-cd.yml`)

This file defines what happens automatically:

```yaml
on:
  push:
    branches: [ main, develop ]  # Triggers on push to these branches
  pull_request:
    branches: [ main ]           # Triggers on PR to main
```

**Translation**: "Run this pipeline when code is pushed to main/develop OR when someone creates a pull request to main"

### 4.2 Jobs that Run

1. **quality-checks**: Code formatting, linting, security
2. **test**: Run all tests with real database
3. **build**: Create Docker images
4. **integration-test**: Test the full system
5. **security**: Scan for vulnerabilities
6. **deploy-staging**: Auto-deploy to staging (develop branch)
7. **deploy-production**: Auto-deploy to production (main branch)

## Step 5: Your First Pull Request

### 5.1 Create a Feature Branch

```bash
# Create new branch
git checkout -b feature/add-new-endpoint

# Make some changes (edit a file)
echo "# New feature" >> CHANGELOG.md

# Commit changes
git add .
git commit -m "Add new feature documentation"

# Push branch
git push origin feature/add-new-endpoint
```

### 5.2 Create Pull Request

1. Go to your GitHub repository
2. You'll see a yellow banner: "Compare & pull request"
3. Click it
4. Fill in title: "Add new feature documentation"
5. Click "Create pull request"

### 5.3 Watch PR Checks

✨ **GitHub Actions automatically runs PR checks!**

You'll see:
- ✅ **Code review** (checks for issues)
- ✅ **Coverage check** (test coverage)
- ✅ **Performance impact** (analyzes changes)
- ✅ **Security precheck** (security scan)

## Step 6: Deployment Setup (Optional)

For automatic deployment, you need to set up:

### 6.1 GitHub Secrets

1. Go to your repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. Add these secrets:

```
Name: AWS_ACCESS_KEY_ID
Value: your_aws_access_key

Name: AWS_SECRET_ACCESS_KEY  
Value: your_aws_secret_key

Name: SLACK_WEBHOOK_URL
Value: your_slack_webhook (optional)
```

### 6.2 GitHub Environments

1. Go to **Settings** → **Environments**
2. Click **"New environment"**
3. Create two environments:
   - `staging` (for testing)
   - `production` (for live site)

## Step 7: Understanding the Magic ✨

### What Happens Automatically:

1. **Push to `develop`** → Auto-deploys to staging
2. **Push to `main`** → Auto-deploys to production
3. **Create PR** → Runs all quality checks
4. **Merge PR** → Triggers deployment pipeline

### No Manual Work Needed:

- ✅ Tests run automatically
- ✅ Code quality checked automatically  
- ✅ Security scanned automatically
- ✅ Docker images built automatically
- ✅ Deployment happens automatically
- ✅ Notifications sent automatically

## Step 8: Common GitHub Actions Commands

### View Workflow Status
```bash
# Install GitHub CLI (optional)
gh workflow list
gh workflow view
gh run list
```

### Re-run Failed Workflows
1. Go to Actions tab
2. Click failed workflow
3. Click "Re-run all jobs"

### Download Artifacts
1. Click on completed workflow
2. Scroll to "Artifacts" section
3. Download coverage reports, security reports, etc.

## Troubleshooting

### ❌ First Run Fails?

**Common issues:**

1. **Missing Python dependencies**
   - Fix: Check `requirements.txt` is complete
   
2. **Test database issues**
   - Fix: Tests create temporary database automatically
   
3. **Docker build fails**
   - Fix: Check Dockerfile syntax

### ❌ Secrets Not Working?

1. Check secret names match exactly
2. Verify they're set in repository settings
3. Make sure you're using the right environment

### ❌ Too Many API Calls?

GitHub Actions has limits:
- **Public repos**: Unlimited
- **Private repos**: 2,000 minutes/month free

## Next Steps

### 1. Monitor Your Pipeline
- Check Actions tab regularly
- Review failed builds immediately
- Monitor coverage reports

### 2. Customize Workflows
- Edit `.github/workflows/ci-cd.yml`
- Add custom steps
- Modify deployment targets

### 3. Add More Automation
- Automatic dependency updates (Dependabot)
- Security monitoring
- Performance benchmarks

## Benefits You Get Immediately

✅ **Automatic Testing**: Every code change is tested  
✅ **Code Quality**: Consistent formatting and linting  
✅ **Security**: Vulnerability scanning on every change  
✅ **Fast Feedback**: Know within minutes if code breaks  
✅ **Deployment Confidence**: Tested code only reaches production  
✅ **Team Collaboration**: PR reviews with automatic checks  

## Visual Dashboard

After setup, you'll have a beautiful dashboard showing:

- 📊 **Test Results**: Pass/fail status
- 🔒 **Security Status**: Vulnerability reports  
- 📈 **Coverage**: Code coverage trends
- 🚀 **Deployments**: Staging/production status
- ⚡ **Performance**: Load test results

**GitHub Actions transforms your development workflow from manual to fully automated!** 🎉