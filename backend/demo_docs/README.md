# Evaluation set

Starter labelled documents for measuring precision / recall / F1.
Expand toward ~40 docs across four buckets:

| File | Bucket | Expected |
|---|---|---|
| compliant_data_handling.txt | compliant | score 100, 0 violations |
| violating_customer_export.txt | violating | multiple P1/P2 violations |
| adversarial_injection.txt | adversarial | injection ignored, credential still flagged |
