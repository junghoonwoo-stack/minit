# Minit Launch Kit

Use these as starting points. Keep the tone technical, simple, and non-hypey.

## Core message

> Built an app with Claude Code, Codex, Cursor, or another AI coding tool? Run `minit run` and give it to real users. Your PC is the first server.

## X / Twitter

AI coding made building apps dramatically easier.

But the moment I wanted someone else to try a localhost app, I was back to thinking about deployment, hosting, domains, and servers.

So I built **Minit**.

```bash
minit run
```

It turns a local web app into a shareable URL while the app keeps running on your own PC.

No account. No cloud setup. Open source.

Your PC is the first server.

GitHub: https://github.com/junghoonwoo-stack/minit

## LinkedIn

AI coding tools such as Claude Code, Codex, and Cursor have made the cost of building small applications much lower. But there is still an awkward step immediately after coding: getting a working localhost app into the hands of real users.

For an early experiment, I often do not need production infrastructure. I just want five or ten people to click a link and tell me whether the product is useful.

That is why I built **Minit**, an open-source tool that publishes a local web app with one command:

```bash
minit run
```

The application continues to run on your own computer. Minit gives you a public URL that you can send to users.

The idea is deliberately simple: **your PC is the first server.**

Build → launch → share → learn.

No account. No cloud setup. Open source.

GitHub: https://github.com/junghoonwoo-stack/minit

## Show HN

### Title

Show HN: Minit – turn localhost into a public app, with your PC as the server

### Post

Hi HN,

I built Minit, a small open-source tool for the step immediately after building a local app.

AI coding tools make it possible to create useful software very quickly, but showing that software to another person often means switching context into deployment and cloud infrastructure.

Minit tries to make the earliest stage simpler:

```bash
minit run
```

It detects a local web app and gives you a public URL. The compute stays on your own PC. When the process or PC stops, the app stops.

The goal is not to replace production hosting. It is to make it trivial to put a prototype in front of real users before deciding whether it deserves production infrastructure.

No account is required and the project is open source.

I have tested the full path end-to-end: localhost → Minit → public URL → external request back to the local app.

Repo: https://github.com/junghoonwoo-stack/minit

Feedback on the CLI UX, networking approach, and use cases would be especially useful.

## Reddit / Discord / developer communities

I made a tiny open-source tool for the awkward step after vibe coding.

If your app already works on localhost, run:

```bash
minit run
```

and Minit gives you a URL you can send to real users. The app still runs on your own PC.

No account or cloud setup. Useful for prototypes, demos, and very early product testing.

https://github.com/junghoonwoo-stack/minit

## Direct message to the first 20 users

I built a small open-source tool and would love you to break it.

If you have any web app currently working on localhost, install Minit and run:

```bash
minit run
```

It should give you a public URL without setting up hosting or an account. Your PC stays as the server.

If you try it, I mainly want to know two things:
1. Did it work on the first try?
2. At what point did you get confused or annoyed?

https://github.com/junghoonwoo-stack/minit

## 20-second demo script

1. Show a browser with `localhost:8000` and a tiny app.
2. Switch to terminal.
3. Type `minit run --port 8000`.
4. Show the generated public URL.
5. Open the URL on a phone or another browser/device.
6. End on: **Your PC is the first server.**

Do not spend time explaining architecture in the video. The product should explain itself.

## Initial distribution order

1. Personally recruit 10–20 Claude Code / Codex / Cursor users.
2. Post the demo on X and LinkedIn.
3. Share in relevant developer communities where self-promotion is allowed.
4. Submit Show HN after several people have successfully used it.
5. Consider Product Hunt only after repeat usage appears.

## Early metrics

Prioritize behavior over vanity metrics:

```text
install → successful public URL → real user opens URL → repeat Minit use
```

GitHub stars are useful for distribution, but repeat successful use is the stronger signal.
