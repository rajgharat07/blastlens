# Examples

## shopfleet

Tiny multi-service commerce fixture with real dependency edges:

- `services/*/service.yaml` — `depends_on`, shared configs, env hostnames  
- `k8s/` — Deployment/Service selectors + ConfigMap/Secret refs  
- `terraform/` — SQS + Lambda with `depends_on`  
- `.blastlens/catalog.yaml` — criticality hints for scoring  

`legacy-billing` is intentionally orphaned (in-graph, no edge from checkout) so contradiction drops are demoable.

## changes/

- `risky-checkout.diff` — image bump + retry note on checkout  
- `proposals/risky-checkout.json` — Worker-Agent-shaped proposal exercising all three tiers  
