# Minit Product Principles

Minit does one thing first:

> **Take a web app that already works on localhost and make it easy to share with another person.**

## Local first

Your app keeps running on your own computer. Minit should not require you to move your code, change frameworks, or create infrastructure just to let someone try it.

> **Your PC is the first server.**

## No account for the core workflow

The basic path stays simple:

```text
build → localhost → minit run → shareable URL → feedback
```

`minit run` should not require a Minit account.

## Work with what already runs

Minit is not an application framework. If your web app is already listening on a local HTTP port, Minit should work around it rather than asking you to rebuild it around Minit.

## Temporary by default

A shared app is live while Minit and the local computer remain running. Stop the process and the public path closes.

This makes the default workflow appropriate for prototypes, demos, and early user testing rather than production hosting.

## Explicit security

Publishing localhost changes the security boundary of an application. Minit should make that visible, avoid pretending that an unguessable URL is authentication, and keep security-sensitive behavior explicit.

See [SECURITY.md](../SECURITY.md).

## Small dependency footprint

Installation and first run should require as little system knowledge and setup as practical. Infrastructure details should stay out of the way unless the user needs them.

## Transparent and portable

Minit should make its behavior understandable. The networking layer is an implementation detail, not the product itself, and should remain replaceable over time.

A Minit project also receives a persistent local identity so the project can evolve without losing continuity.

## Category

**Micro IT** — software small enough to be built, launched, and initially operated by one person.
