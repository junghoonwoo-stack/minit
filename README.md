# Minit

**From localhost to real users in one command.**

> **Your PC is the first server.**

Minit is an open-source tool for people who build apps with Claude Code, Codex, Cursor, or other AI coding tools and want real users to try them immediately — without setting up cloud infrastructure first.

Your app keeps running on your own PC. Minit gives it a shareable URL.

![Minit demo](assets/demo.svg)

No account. No cloud setup. No separate server software.

## Install

```bash
git clone https://github.com/junghoonwoo-stack/minit.git
cd minit
pip install -e .
```

## Use

Run your app locally, then:

```bash
minit run
```

Or specify the port:

```bash
minit run --port 8501
```

Minit returns a public URL. Send it to users. Keep your PC on while the app is being used. Press `Ctrl+C` to stop.

## Try it in one minute

```bash
cd examples/hello-minit
python -m http.server 8000
```

In another terminal:

```bash
minit run --port 8000
```

Open the generated URL from another device.

## Why Minit?

AI coding made building software much easier. Getting a local app in front of real users should be just as easy.

```text
Build → launch → share → learn
```

Minit is open source and focused first on making this local-to-live experience as simple as possible.

---

# 한글 설명

**Minit은 내 PC에서 실행 중인 앱을 바로 외부 사용자에게 공개할 수 있게 해주는 오픈소스 도구입니다.**

Claude Code, Codex, Cursor 등으로 앱을 빠르게 만들었지만, 클라우드나 서버 설정 없이 바로 실제 사용자에게 보여주고 싶을 때 사용합니다.

```text
AI로 앱 개발 → 내 PC에서 실행 → minit run → URL 공유 → 실제 사용자 테스트
```

## 설치

```bash
git clone https://github.com/junghoonwoo-stack/minit.git
cd minit
pip install -e .
```

## 사용

앱을 실행한 뒤:

```bash
minit run
```

생성된 링크를 사용자에게 보내면 됩니다. **내 PC가 첫 번째 서버**가 되고, PC를 끄면 서비스도 종료됩니다.

Minit의 첫 번째 목표는 단순합니다.

> **AI로 만든 앱을 localhost에서 실제 사용자에게 가장 쉽게 보여주는 것.**

가입도, 별도 서버도, 클라우드 설정도 최대한 필요 없게 만드는 것을 지향합니다.

## License

Apache License 2.0.
