CREATE TABLE IF NOT EXISTS fx_rates (
    currency VARCHAR(3) PRIMARY KEY,
    rate_to_usd NUMERIC(20, 10) NOT NULL,
    CONSTRAINT ck_fx_rates_currency_format
        CHECK (currency = upper(currency) AND char_length(currency) = 3),
    CONSTRAINT ck_fx_rates_rate_positive CHECK (rate_to_usd > 0)
);

CREATE TABLE IF NOT EXISTS countries (
    code VARCHAR(2) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    currency VARCHAR(3) NOT NULL REFERENCES fx_rates(currency) ON DELETE RESTRICT,
    CONSTRAINT uq_countries_code_currency UNIQUE (code, currency),
    CONSTRAINT ck_countries_code_format
        CHECK (code = upper(code) AND char_length(code) = 2),
    CONSTRAINT ck_countries_name_not_blank CHECK (char_length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS departments (
    name VARCHAR(100) PRIMARY KEY,
    CONSTRAINT ck_departments_name_not_blank CHECK (char_length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS employees (
    id BIGSERIAL PRIMARY KEY,
    employee_id VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    country VARCHAR(2) NOT NULL,
    department VARCHAR(100) NOT NULL REFERENCES departments(name) ON DELETE RESTRICT,
    role VARCHAR(200) NOT NULL,
    annual_salary_native NUMERIC(18, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL REFERENCES fx_rates(currency) ON DELETE RESTRICT,
    salary_usd NUMERIC(18, 2) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    deactivated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_employees_country_currency
        FOREIGN KEY (country, currency)
        REFERENCES countries(code, currency)
        ON DELETE RESTRICT,
    CONSTRAINT ck_employees_employee_id_not_blank
        CHECK (char_length(trim(employee_id)) > 0),
    CONSTRAINT ck_employees_name_not_blank CHECK (char_length(trim(name)) > 0),
    CONSTRAINT ck_employees_role_not_blank CHECK (char_length(trim(role)) > 0),
    CONSTRAINT ck_employees_native_salary_positive CHECK (annual_salary_native > 0),
    CONSTRAINT ck_employees_usd_salary_positive CHECK (salary_usd > 0),
    CONSTRAINT ck_employees_deactivation_state CHECK (
        (is_active AND deactivated_at IS NULL)
        OR (NOT is_active AND deactivated_at IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS ix_employees_active_name
    ON employees (is_active, name);
CREATE INDEX IF NOT EXISTS ix_employees_active_country
    ON employees (is_active, country);
CREATE INDEX IF NOT EXISTS ix_employees_active_department
    ON employees (is_active, department);
CREATE INDEX IF NOT EXISTS ix_employees_active_salary_usd
    ON employees (is_active, salary_usd);

