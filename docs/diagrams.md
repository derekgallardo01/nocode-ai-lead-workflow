# Diagrams

Beyond the inline ones in [architecture.md](architecture.md).

## 1. Decision tree — what happens to each lead

```mermaid
flowchart TB
    L["Raw lead arrives"] --> D{"Email seen<br/>this batch?"}
    D -- "yes" --> M["Merge into primary lead<br/>(merged_from tracks it)"]
    D -- "no" --> P["Process_leads()"]
    M --> SKIP["No further processing<br/>for this duplicate"]
    P --> C["Classify (RULES table)"]
    C --> CF{"Confidence?"}
    CF -- "strong / weak<br/>(matched a category)" --> CHK{"Spam<br/>category?"}
    CF -- "fallback<br/>(no keywords)" --> HR["Human-review queue<br/>(for_human_review.json)"]
    CHK -- "yes, strong" --> SP["CRM only<br/>(no follow-up)"]
    CHK -- "yes, weak" --> HR
    CHK -- "no" --> FU["Follow-up drafted<br/>(follow_ups.json)"]
    FU --> CRM["CRM row<br/>(crm.csv/json)"]
    HR --> CRM
    SP --> CRM
```

## 2. Sequence — the default 9-lead run end-to-end

```mermaid
sequenceDiagram
    autonumber
    participant U as User/Schedule
    participant R as run()
    participant D as dedupe
    participant P as process_leads
    participant S as save_crm
    participant H as human_review_queue
    participant F as follow_ups

    U->>R: run("data/leads.json", "out/")
    R->>R: load 9 raw leads
    R->>D: dedupe(raw_leads)
    D->>D: collapse by normalized email
    D-->>R: (7 unique, 2 merged pairs)
    R->>P: process_leads(deduped, merged_into=...)
    loop per lead
      P->>P: _classify → (category, confidence, matched_keywords)
      P->>P: needs_review = (confidence==fallback) OR (spam AND weak)
    end
    P-->>R: 7 Processed records
    R->>S: save_crm(processed, out_dir)
    S->>S: write crm.csv + crm.json
    R->>H: human_review_queue(processed)
    H-->>R: [1] (the fallback-confidence lead)
    R->>F: follow_ups(processed)
    F-->>R: [5] (7 - 1 spam - 1 human-review)
    R-->>U: {raw:9, deduped:7, follow_ups:5, human_review:1, ...}
```

## 3. State — a single lead through the pipeline

```mermaid
stateDiagram-v2
    [*] --> Raw: arrives via channel
    Raw --> Duplicate: same normalized email as earlier lead
    Raw --> Unique: first occurrence of this email
    Duplicate --> Merged: merged_from on primary
    Merged --> [*]: no further processing
    Unique --> Classified: _classify returns (cat, conf, matches)
    Classified --> StrongOrWeak: confidence in {strong, weak}
    Classified --> Fallback: confidence == "fallback"
    StrongOrWeak --> Spam: category == spam_or_irrelevant
    StrongOrWeak --> AutoReply: category != spam
    Spam --> WeakSpamReview: weak signal — needs human eye
    Spam --> Logged: strong spam — just logged
    Fallback --> HumanReview: queued for triage
    WeakSpamReview --> HumanReview
    AutoReply --> FollowUp: draft queued in follow_ups.json
    HumanReview --> CRM: also saved to crm
    FollowUp --> CRM
    Logged --> CRM
    CRM --> [*]
```

## 4. Channel split — same pipeline, different data shape

```mermaid
flowchart LR
    subgraph DEFAULT["Default (B2B SaaS)"]
      D1["data/leads.json"]
      D1 --> ME["dedupe + classify + ... (unchanged engine)"]
    end
    subgraph REALESTATE["Real-estate brokerage"]
      D2["data/leads-real-estate.json"]
      D2 --> ME
    end
    ME --> OUT["Same outputs:<br/>crm · follow_ups · for_human_review"]
```

Both datasets prove the pipeline works without code changes — only the
input file path changes. The eval set asserts the expected counts for
each.
