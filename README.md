# shimpz-browser

A headful `google-chrome-stable` instance driven over CDP inside an isolated container and exposed to
the rest of the stack only through browser-agent's narrow, audited HTTP API. When the operator
configures a residential proxy, Chrome routes through the authenticated relay in this container.

---
Part of the **[Shimpz](https://github.com/roxygens/shimpz)** stack — a self-hosted, voice-driven autonomous agent.
