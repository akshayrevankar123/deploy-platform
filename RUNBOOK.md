# RUNBOOK: from your laptop to a live URL

Do the parts in order. Each part ends with a check. If a check fails, stop and fix it before moving on.
All commands are for **Windows PowerShell** unless a heading says **EC2 server**.

**Golden rules**
- Never paste passwords, tokens, `.env` contents or `.pem` keys into chat, GitHub issues or screenshots.
- Never commit `.env`, `*.pem` or `*.db`. The `.gitignore` already blocks them; still check `git status` before every commit.
- Set the AWS budget alert (Part 4) BEFORE you launch anything.
- Only deploy and scan projects you own.

---

## Part 1: Run it on your laptop (no Docker)

Window 1, backend:
```powershell
cd C:\Users\ASUS\Projects\deploy-platform\backend
.\venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest -q
$env:SECRET_KEY = "any-long-random-text-for-local-use"
uvicorn app.main:app --reload
```
Setting `SECRET_KEY` keeps your login valid when the server restarts. Without it a random key is made every start, which is why tokens suddenly stopped working earlier.

Window 2, frontend (needs Node.js, check with `node --version`):
```powershell
cd C:\Users\ASUS\Projects\deploy-platform\frontend
npm install
npm run dev
```
**Check:** http://localhost:5173 shows the login page. Register, log in, add a project, click Scan.

## Part 2: Run it in Docker on your laptop

Open Docker Desktop and wait for "Engine running". Stop the uvicorn window first (Ctrl+C) so port 8000 is free.
```powershell
cd C:\Users\ASUS\Projects\deploy-platform
docker build -t deploy-platform:local .
docker run --rm -p 8000:8000 -e SECRET_KEY=local-test-key deploy-platform:local
```
The first build takes a few minutes (it builds the React app too).
**Check:** http://localhost:8000 shows the dashboard and http://localhost:8000/health shows `{"status":"ok"}`. Press Ctrl+C to stop.

Optional, with PostgreSQL:
```powershell
Copy-Item .env.example .env
notepad .env        # replace the two "change-me" values with long random text
docker compose up --build
```
Stop with Ctrl+C, then `docker compose down`. (`docker compose down -v` also deletes the database volume.)

## Part 3: GitHub

1. On github.com create a new **empty** repository called `deploy-platform` (Public is easiest: Actions minutes are free for public repos). Do not add a README or .gitignore there.
2. In PowerShell:
```powershell
cd C:\Users\ASUS\Projects\deploy-platform
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git init -b main
git add .
git status
```
**Read the `git status` list.** There must be NO `.env`, `venv`, `node_modules`, `*.db` or `*.pem`. Then:
```powershell
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR-USERNAME/deploy-platform.git
git push -u origin main
```
A browser window may ask you to sign in to GitHub. That is normal and safe.

**Check:** repo page > **Actions** tab > the **CI** workflow runs. Expect 4 jobs: Run tests, Secret scan, Dependency scan, Docker build + image scan. If one fails, open it, copy the failing step's error and ask for help. The most likely causes are a Trivy or Gitleaks action version issue.

## Part 4: AWS safety setup (costs money if you skip this)

1. Sign in to the AWS Console. Top right, pick the region **Asia Pacific (Mumbai) ap-south-1** and use it for everything.
2. Billing and Cost Management > **Credits**: note the amount left and the **expiry date**.
3. Billing and Cost Management > **Budgets** > Create budget > Cost budget > monthly, amount **10 USD**, alerts at 50% and 80% to your email. Confirm the email.
4. Never create: NAT Gateway, Load Balancer, RDS, Elastic IPs you forget about, extra EC2 instances.

**Rough running cost** if one small instance stays on 24/7: about USD 10 to 12 per month (t3.micro compute + the public IPv4 address + 8 GB disk). Prices change, so check the AWS pricing page and your Billing page. Stopping the instance when idle cuts most of it.

## Part 5: Launch ONE EC2 instance

Console > EC2 > **Launch instance** (this starts billing):
- Name: `deploy-platform`
- AMI: **Amazon Linux 2023**
- Instance type: **t3.micro** (or t2.micro if that is the one marked free-tier eligible for your account)
- Key pair: **Create new key pair** > RSA > `.pem` > name it `deploy-platform-key`. Save the downloaded file to `C:\Users\ASUS\.ssh\` and never share or commit it.
- Network settings > Create security group with only:
  - **SSH (22)**: source **My IP** for now
  - **HTTP (80)**: source **Anywhere**
  - Nothing else. In particular never open 5432 (PostgreSQL) or 8000.
- Storage: 8 GiB gp3 (the default)
- Launch. Wait until the state is **Running**, then copy the **Public IPv4 address** (call it `HOST`).

**Fix key permissions** (Windows SSH refuses keys that other users can read):
```powershell
icacls C:\Users\ASUS\.ssh\deploy-platform-key.pem /inheritance:r
icacls C:\Users\ASUS\.ssh\deploy-platform-key.pem /grant:r "$($env:USERNAME):(R)"
```
**Connect:**
```powershell
ssh -i C:\Users\ASUS\.ssh\deploy-platform-key.pem ec2-user@HOST
```
Type `yes` the first time. **Check:** the prompt becomes `[ec2-user@ip-... ~]$`.

## Part 6: Prepare the server (EC2 server)

From PowerShell on your laptop, copy the scripts up:
```powershell
cd C:\Users\ASUS\Projects\deploy-platform
scp -i C:\Users\ASUS\.ssh\deploy-platform-key.pem deploy\ec2-setup.sh deploy\remote-deploy.sh deploy\remote-report.sh ec2-user@HOST:/home/ec2-user/
```
Then connect with `ssh` as in Part 5 and run on the server:
```bash
sed -i 's/\r$//' *.sh        # removes Windows line endings if any slipped in
bash ec2-setup.sh
exit
```
Reconnect (so the docker group applies) and check `docker ps` works without errors.
The script generated `SECRET_KEY` and `DEPLOY_REPORT_TOKEN` inside `/opt/deploy-platform/.env` on the server. You never need to see or copy them.

## Part 7: First manual deploy

Manual first, automation second. On your laptop:
1. Create a free account at hub.docker.com. Account settings > Personal access tokens > create a token with **Read & Write**. You will use it as a password for `docker login`; do not paste it anywhere else.
```powershell
docker login -u YOUR-DOCKERHUB-USERNAME
cd C:\Users\ASUS\Projects\deploy-platform
docker build -t YOUR-DOCKERHUB-USERNAME/deploy-platform:manual1 .
docker push YOUR-DOCKERHUB-USERNAME/deploy-platform:manual1
```
2. Deploy it through SSH:
```powershell
ssh -i C:\Users\ASUS\.ssh\deploy-platform-key.pem ec2-user@HOST "IMAGE='YOUR-DOCKERHUB-USERNAME/deploy-platform:manual1' bash /home/ec2-user/remote-deploy.sh"
```
**Check:** the script ends with `New version is healthy`, and `http://HOST` in your browser shows the dashboard. Register an account there.

Useful server commands (after `ssh`):
```bash
docker ps                                  # is it running?
docker logs --tail 50 deploy-platform      # recent logs
docker restart deploy-platform             # restart
free -m && df -h                           # memory and disk
```

## Part 8: Automatic deployment (CI/CD)

1. **Dedicated deploy key** (so you can revoke it without touching your admin key):
```powershell
ssh-keygen -t ed25519 -f $HOME\.ssh\deploy_platform_ci -N '""'
Get-Content $HOME\.ssh\deploy_platform_ci.pub
```
Copy the printed single line. On the server (`ssh` in) run: `echo "PASTE-THE-LINE-HERE" >> ~/.ssh/authorized_keys`
2. **Open SSH for GitHub.** GitHub's runners use changing IP addresses, so the SSH rule must allow `0.0.0.0/0` (EC2 > Security Groups > Edit inbound rules > SSH 22 > Anywhere). This is a real trade-off: access still needs the private key (password login is off by default on Amazon Linux), but port 22 becomes visible to the internet. Mention it in your report as a limitation.
3. **Add GitHub secrets**: repo > Settings > Secrets and variables > Actions > New repository secret:

| Secret | Value |
|---|---|
| `DOCKERHUB_USERNAME` | your Docker Hub username |
| `DOCKERHUB_TOKEN` | the Docker Hub access token |
| `EC2_HOST` | the server's public IP |
| `EC2_USER` | `ec2-user` |
| `EC2_SSH_KEY` | the PRIVATE deploy key. Copy it without displaying it: `Get-Content $HOME\.ssh\deploy_platform_ci -Raw \| Set-Clipboard` then paste into the secret box |

4. **Show deployments in your dashboard:** open `http://HOST`, log in, add a project with your own `deploy-platform` repo URL. Note its project id (the first project is normally `1`). In GitHub: Settings > Secrets and variables > Actions > **Variables** tab > new variable `PLATFORM_PROJECT_ID` = that number.
5. Push any small change to `main`. **Check:** Actions shows **CI** then **Deploy** running. When both are green, `http://HOST` serves the new version and the dashboard's deployment history shows the entry. You can also start Deploy by hand: Actions > Deploy > Run workflow.

**If a deploy breaks:** `remote-deploy.sh` automatically puts the previous version back and the workflow turns red.

## Part 9: Monitoring and alerts

- Dashboard > **Monitoring** shows server CPU, memory and disk, plus uptime % and response time for each deployed project (click **Check now** for a fresh check).
- The **Uptime check** workflow calls `/health` every 15 minutes. If the app is down, the run fails and GitHub emails you. This is a simple free alert, not a real pager.
- Test it: on the server run `docker stop deploy-platform`, wait for the next uptime run (or run it from the Actions tab), watch it fail, then `docker start deploy-platform`.

## Part 10: Stop spending (do this after every session and after your viva)

- **Pause:** EC2 > Instances > select > Instance state > **Stop**. Compute billing stops; the disk costs a little. The public IP changes on the next start, so update the `EC2_HOST` secret. Also **disable the Uptime check workflow** (Actions > Uptime check > ... > Disable workflow) or it will email you failures.
- **Finish:** Instance state > **Terminate**. Then check EC2 > **Volumes** (should be empty), **Elastic IPs** (none), and Billing > Bills the next day for any charge.
- Delete the Docker Hub token and the GitHub secrets when you are done, and delete the `deploy_platform_ci` key line from the server if it still exists.

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `ssh` says "UNPROTECTED PRIVATE KEY FILE" | Run the two `icacls` commands in Part 5 |
| `ssh` times out | Security group has no SSH rule for your current IP (your IP changes). Edit the rule to "My IP" again |
| `bash\r: No such file` or `$'\r': command not found` on the server | Windows line endings. Run `sed -i 's/\r$//' *.sh` on the server |
| `permission denied ... docker.sock` | You did not log out and in after `ec2-setup.sh` |
| `http://HOST` does not load but `docker ps` shows it running | Security group is missing HTTP 80 from Anywhere |
| Deploy job: "Missing GitHub secret: X" | Add that secret (names are case sensitive) |
| Deploy job fails at the image scan | A CRITICAL vulnerability with a fix exists. Update the base image or dependency, push again |
| Deploy job fails at "Health check from outside AWS" | Port 80 closed, or the container crashed. SSH in and run `docker logs deploy-platform` |
| Dashboard shows "Not logged in" after a restart | The token expired (60 min) or `SECRET_KEY` changed. Log in again |
| Report step skipped | `PLATFORM_PROJECT_ID` variable missing, or the project does not exist yet on the deployed app |
| Uptime emails keep coming | The instance is stopped. Disable the Uptime check workflow |

## Known limits (be honest about these in your viva)

- The site is served over plain **HTTP**. Passwords and tokens travel unencrypted. HTTPS needs a domain name and a certificate (for example Caddy or Nginx with Let's Encrypt). This is future scope.
- One server, one container, SQLite file on a Docker volume. No backups, no scaling.
- The platform pipeline deploys **this** application. The "Deploy project" button records a request; deploying a different user's repo uses the same pipeline pattern (see `sample-app/.github/workflows/ci.yml`), but running strangers' code safely needs sandboxing that this MVP does not have.
- A clean scan never proves an application is secure.
