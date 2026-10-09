# Browser workflow validation

The browser interface follows Ask → Review → Route → Run → Results. The current suite
uses accessible roles, labels, and text to exercise requests, routing, results, history,
data intake, responsiveness, and representative evidence boundaries.

Run `npm run e2e` in `praxis_vc_react` after following the frontend setup instructions.
Offline browser tests validate software behavior; external LLM and scientific model
validation require their separately provisioned inputs and explicit opt-in.

The historical three-test snapshot has been superseded by the current suite. Refer to
[the testing guide](../../docs/TESTING.md) and current CI output for the executed count.
