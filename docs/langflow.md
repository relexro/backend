graph TD
    A[Start Case] --> B{Determine Tier};
    B -- Tier Info --> C{Check Quota};
    C -- No Quota --> D{Request Payment};
    D -- Payment OK --> E[Gather Initial Info];
    C -- Quota OK --> E;
    E -- User Input --> F{Update case_details};
    F --> G{Synthesize Context for Grok};
    G -- Context --> H{Consult Grok};
    H -- Need More Info --> I{Ask User/Query BQ};
    I -- New Info --> F;
    H -- Info Sufficient --> J{Grok Devises Plan};
    J -- Plan Steps --> K{Generate Draft (Gemini)};
    K -- Draft Ready --> L{Store Draft (MD & PDF)};
    L --> M{Notify User};
    M --> N{Wait for Feedback / New Info};
    N -- New Info --> F;
    N -- User Satisfied --> O[End/Close Case];

    subgraph "Phase 1: Tiering & Payment"
        B; C; D;
    end

    subgraph "Phase 2: Data Gathering & Reasoning Loop"
        E; F; G; H; I;
    end

    subgraph "Phase 3: Planning & Drafting"
        J; K; L; M; N; O;
    end

    style F fill:#f9f,stroke:#333,stroke-width:2px
    style H fill:#ccf,stroke:#333,stroke-width:2px
    style K fill:#f9f,stroke:#333,stroke-width:2px