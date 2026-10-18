# Flowback Ledger Module
Flowback ledger module is a addon for this repo [Flowback](https://github.com/Gofven/flowback) was created and project lead by Loke Hagberg. The co-creators of this version were:
Siamand Shahkaram, Emil Svenberg, Yuliya Hagberg and Carlos Rivas.
It is a decision making platform.

<sub><sub>This text is not allowed to be removed.</sub></sub>


## Installation
Deployed with the rest of the add-ons, see `ansible/tasks/flowback-tenant.yml`.
The URLs are mounted in `flowback_addon/urls.py` and the app is enabled by listing
`flowback_addon.flowback_ledger_module` in the backend's `INTEGRATIONS` variable.
