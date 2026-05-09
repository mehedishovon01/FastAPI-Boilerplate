"""Pure helper functions and reusable schemas.

Anything here MUST be:

* Pure — no I/O, no database, no network, no env-var lookups.
* Domain-agnostic — usable by any app.

If your helper talks to the outside world (SMTP, Redis, S3, Stripe,
queues, ...), it is an *infrastructure service* — put it in
``src/services/`` instead.
"""
