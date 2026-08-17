# Minit

**From localhost to real users in one command.**

> **Your PC is the first server. Launch first. Cloud later.**

Minit is an open-source tool for people who build apps with Claude Code, Codex, Cursor, or other AI coding tools and want real users to try them immediately — without setting up cloud infrastructure first.

Your app keeps running on your own PC. Minit gives it a shareable URL.

```text
AI coding → localhost → minit run → shareable URL → real users
                              ↑
                         your own PC
```

## Install

```bash
git clone https://github.com/junghoonwoo-stack/minit.git
cd minit
pip install -e .
```

No separate tunnel or server software installation is required. Minit prepares the networking it needs automatically on first run.

## Use

Run your app locally:

```bash
streamlit run app.py
# or python app.py
# or npm run dev
```

Then:

```bash
minit run
```

Or specify the port:

```bash
minit run --port 8501
```

Minit returns a public URL:

```text
✓ Local app: http://127.0.0.1:8501
✓ Live URL:  https://xxxxx.example.com
✓ Compute:   this PC
```

Send the link to users. Keep your PC on while the app is being used. Press `Ctrl+C` to stop.

Minit automatically creates a persistent app identity in `.minit/app.json`. That identity is designed to stay with the app when it later moves from your PC to Minit-hosted services.

## Open source first. Hosted when useful.

Minit follows a simple model:

```text
Local OSS → Real users → Minit Cloud → Minit Managed
```

- **Minit OSS** — run from your PC for free.
- **Minit Cloud** — stable URL, auth, logs, analytics and managed networking.
- **Minit Managed** — move the same app to always-on managed compute when your PC is no longer enough.
- **Enterprise** — later: SSO, security policies, audit logs and central app management.

The goal is to make the transition seamless: **same app, same identity, eventually the same URL — only the runtime changes.**

> **Local first. Managed later.**

More: [Business Model](docs/BUSINESS_MODEL.md)

---

# 한글 설명

**Minit은 내 PC에서 실행 중인 앱을 바로 외부 사용자에게 공개할 수 있게 해주는 오픈소스 도구입니다.**

Claude Code, Codex, Cursor 등으로 앱을 빠르게 만들었지만 아직 클라우드나 서버 운영을 배우고 싶지 않은 사람을 위한 도구입니다.

```text
AI로 앱 개발 → 내 PC에서 실행 → minit run → URL 공유 → 실제 사용자 테스트
```

## 설치

```bash
git clone https://github.com/junghoonwoo-stack/minit.git
cd minit
pip install -e .
```

별도의 터널 프로그램이나 서버 소프트웨어를 설치할 필요가 없습니다.

## 사용

```bash
streamlit run app.py
minit run
```

생성된 링크를 사용자에게 보내면 됩니다. 내 PC가 첫 번째 서버가 되고, PC를 끄면 서비스도 종료됩니다.

Minit은 처음에는 무료 오픈소스로 내 PC에서 사용하고, 실제 사용자가 생기면 **stable URL·인증·로그 등을 제공하는 Minit Cloud**, 더 커지면 **항상 켜져 있는 Minit Managed**로 자연스럽게 옮기는 구조를 지향합니다.

> **먼저 출시하고, 사용자가 생기면 그때 클라우드로.**

## License

Apache License 2.0.
