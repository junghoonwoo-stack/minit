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

First, run your app locally:

```bash
streamlit run app.py
# or
python app.py
# or
npm run dev
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

## The idea

```text
Build → launch → share → learn
```

Minit is for the stage before you need real cloud hosting.

If nobody uses the app, turn it off. If people love it, move it to managed hosting later.

> **Local first. Managed later.**

---

# 한글 설명

**Minit은 내 PC에서 실행 중인 앱을 바로 외부 사용자에게 공개할 수 있게 해주는 오픈소스 도구입니다.**

Claude Code, Codex, Cursor 등으로 앱을 빠르게 만들었지만, 아직 클라우드나 서버 운영을 배우고 싶지 않은 사람을 위한 도구입니다.

```text
AI로 앱 개발 → 내 PC에서 실행 → minit run → URL 공유 → 실제 사용자 테스트
```

## 설치

```bash
git clone https://github.com/junghoonwoo-stack/minit.git
cd minit
pip install -e .
```

별도의 터널 프로그램이나 서버 소프트웨어를 설치할 필요가 없습니다. 처음 실행할 때 Minit이 필요한 네트워크 구성요소를 자동으로 준비합니다.

## 사용

먼저 앱을 내 PC에서 실행합니다.

```bash
streamlit run app.py
```

그리고:

```bash
minit run
```

그러면 외부 사용자가 접속할 수 있는 URL이 생성됩니다. 링크만 보내면 됩니다.

내 PC가 첫 번째 서버가 됩니다. PC를 끄면 서비스도 종료됩니다. 초기 제품 검증 단계에서는 그것으로 충분하다는 것이 Minit의 생각입니다.

> **먼저 출시하고, 사용자가 생기면 그때 클라우드로.**

## License

Apache License 2.0.
