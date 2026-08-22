# Minit

**From localhost to real users in one command.**

> **Your PC is the first server.**

Minit is an open-source local-first tool for people who build apps with Claude Code, Codex, Cursor, or other AI coding tools.

Today, Minit makes an app already running on your computer reachable through a shareable URL. The direction is broader: make local software easy to run, observe, version, back up, share, and move **without making cloud compute the default runtime**.

Your application process and compute stay on your own machine.

![Minit demo](assets/demo.svg)

No account. No cloud compute setup. No separate app server.

**Website:** https://junghoonwoo-stack.github.io/minit/

## Install

With `pipx`:

```bash
pipx install minit-runtime
```

Or with `uv`:

```bash
uv tool install minit-runtime
```

The Python package is named `minit-runtime`; the command is simply `minit`.

For development:

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

In one terminal, start a tiny local page:

```bash
python -c "from pathlib import Path; p=Path('minit-demo'); p.mkdir(exist_ok=True); (p/'index.html').write_text('Hello from Minit')"
python -m http.server 8000 --directory minit-demo
```

In another terminal:

```bash
minit run --port 8000
```

Open the generated URL from another device.

## Local-first direction

Minit's architectural direction is:

```text
Your machine
  app · data · secrets · keys · compute
             │
             ▼
      Minit Local Manager
  run · connect · protect · observe
  version · backup · share · move
             │
             ▼
 optional encrypted coordination / relay
```

The local machine remains authoritative. Future remote coordination services should not require possession of application plaintext or decryption keys.

This is a design direction, not a claim that all of those management and encryption features are implemented today. See [Architecture](docs/ARCHITECTURE.md) and [Product Principles](docs/PRODUCT.md).

## Security — MVP

`minit run` makes your local app reachable from the public internet. Treat the generated URL as public.

For the current MVP:

- Do not expose apps containing secrets, private files, personal data, or sensitive company data.
- Do not rely on the URL itself as authentication.
- If your app needs access control, add authentication in the app before publishing it.
- Review AI-generated apps for hard-coded API keys, debug endpoints, and unintended file/data access before sharing them.

Minit is currently intended for lightweight prototypes and early user testing, not sensitive or production workloads.

Read the full [Security Policy](SECURITY.md).

## Why Minit?

AI coding made building software much easier. Running that software for a few real people should not automatically require moving it into cloud infrastructure.

```text
Build → run locally → share → learn → keep local software manageable
```

---

# 미닛

**Minit은 내 PC에서 실행 중인 앱을 바로 외부 사용자에게 공개하고, 장기적으로는 로컬 앱을 클라우드처럼 쉽게 관리하기 위한 오픈소스 도구입니다.**

Claude Code, Codex, Cursor 등으로 앱을 빠르게 만들었다면 앱의 코드·데이터·실행 환경을 먼저 내 컴퓨터에 둔 채 실제 사용자에게 보여줄 수 있습니다.

```text
AI로 앱 개발 → 내 PC에서 실행 → minit run → URL 공유 → 실제 사용자 테스트
```

## 설치

`pipx` 사용 시:

```bash
pipx install minit-runtime
```

또는 `uv`:

```bash
uv tool install minit-runtime
```

Python 패키지 이름은 `minit-runtime`이고, 실행 명령은 `minit`입니다.

## 사용

앱을 실행한 뒤:

```bash
minit run
```

생성된 링크를 사용자에게 보내면 됩니다. **내 PC가 첫 번째 서버**가 되고, PC를 끄면 서비스도 종료됩니다.

장기 방향은 앱의 실행·모니터링·버전·백업·공유·이동을 Minit이 관리하되, 앱 코드·데이터·secret·암호화 key의 control은 로컬에 두는 것입니다.

## 보안 — 현재 MVP

`minit run`을 실행하면 로컬 앱이 인터넷에서 접근 가능해집니다. 생성된 URL은 **공개 URL**이라고 생각하는 것이 안전합니다.

현재 MVP에서는 비밀번호·API Key·개인정보·회사 내부자료 등 민감한 정보가 들어 있는 앱은 공개하지 않는 것을 권장합니다. 인증이 필요한 앱이라면 Minit으로 공개하기 전에 앱 자체에 인증을 구현해야 합니다. 특히 AI로 생성한 앱은 hard-coded API key, debug endpoint, 의도하지 않은 파일·데이터 접근이 없는지 확인한 뒤 공유하세요.

현재 Minit은 민감하거나 production 용도보다는 **가벼운 prototype과 초기 사용자 테스트**를 위한 도구입니다.

## License

[Apache License 2.0](LICENSE).
