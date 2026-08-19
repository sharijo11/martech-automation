CREATE TABLE IF NOT EXISTS provider_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lead_id INT NOT NULL,
    task_id INT NULL,
    provider VARCHAR(50) NOT NULL,
    operation VARCHAR(100) NOT NULL,
    mode VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    external_id VARCHAR(255) NULL,
    http_status INT NULL,
    request_payload TEXT NULL,
    response_payload TEXT NULL,
    error_message VARCHAR(500) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_provider_logs_lead_id (lead_id),
    INDEX idx_provider_logs_task_id (task_id),
    CONSTRAINT fk_provider_logs_lead FOREIGN KEY (lead_id) REFERENCES leads(id),
    CONSTRAINT fk_provider_logs_task FOREIGN KEY (task_id) REFERENCES automation_tasks(id)
);
