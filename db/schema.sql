CREATE TABLE bank_customers (
    customer_id         VARCHAR2(30) PRIMARY KEY,
    identity_subject    VARCHAR2(255),
    full_name           VARCHAR2(120) NOT NULL,
    email               VARCHAR2(255) NOT NULL,
    tier                VARCHAR2(40) NOT NULL,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE bank_accounts (
    account_id          VARCHAR2(30) PRIMARY KEY,
    customer_id         VARCHAR2(30) NOT NULL,
    account_name        VARCHAR2(80) NOT NULL,
    account_type        VARCHAR2(20) NOT NULL,
    balance             NUMBER(14,2) NOT NULL,
    currency_code       VARCHAR2(3) DEFAULT 'USD' NOT NULL,
    routing_last4       VARCHAR2(4),
    account_last4       VARCHAR2(4),
    apr                 NUMBER(6,2),
    available_credit    NUMBER(14,2),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_bank_accounts_customer
        FOREIGN KEY (customer_id) REFERENCES bank_customers(customer_id),
    CONSTRAINT chk_bank_accounts_type
        CHECK (account_type IN ('checking', 'savings', 'credit'))
);

CREATE TABLE bank_cards (
    card_id             VARCHAR2(30) PRIMARY KEY,
    customer_id         VARCHAR2(30) NOT NULL,
    linked_account_id   VARCHAR2(30) NOT NULL,
    card_name           VARCHAR2(80) NOT NULL,
    network             VARCHAR2(60) NOT NULL,
    last4               VARCHAR2(4) NOT NULL,
    status              VARCHAR2(30) NOT NULL,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_bank_cards_customer
        FOREIGN KEY (customer_id) REFERENCES bank_customers(customer_id),
    CONSTRAINT fk_bank_cards_account
        FOREIGN KEY (linked_account_id) REFERENCES bank_accounts(account_id),
    CONSTRAINT chk_bank_cards_status
        CHECK (status IN ('active', 'frozen', 'reported_stolen'))
);

CREATE TABLE bank_transactions (
    transaction_id      VARCHAR2(40) PRIMARY KEY,
    account_id          VARCHAR2(30) NOT NULL,
    posted_on           DATE NOT NULL,
    description         VARCHAR2(200) NOT NULL,
    amount              NUMBER(14,2) NOT NULL,
    category            VARCHAR2(40) NOT NULL,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_bank_transactions_account
        FOREIGN KEY (account_id) REFERENCES bank_accounts(account_id)
);

CREATE INDEX idx_bank_accounts_customer
    ON bank_accounts (customer_id);

CREATE INDEX idx_bank_cards_customer
    ON bank_cards (customer_id);

CREATE INDEX idx_bank_transactions_account_date
    ON bank_transactions (account_id, posted_on DESC);
