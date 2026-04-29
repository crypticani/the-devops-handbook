# Module 08: Logging — Resources

---

## 📖 Essential Reading

| Resource | Type | Difficulty | Notes |
|----------|------|------------|-------|
| [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html) | Documentation | Beginner | Official reference — start with "Getting Started" |
| [Grafana Loki Documentation](https://grafana.com/docs/loki/latest/) | Documentation | Beginner | Loki setup, LogQL, and Promtail configuration |
| [The Twelve-Factor App — Logs](https://12factor.net/logs) | Article | Beginner | Why apps should log to stdout — foundational philosophy |
| [Logging Best Practices (Google SRE)](https://sre.google/sre-book/monitoring-distributed-systems/) | Book (Free) | Intermediate | Logging in the context of distributed systems |
| [Kibana User Guide](https://www.elastic.co/guide/en/kibana/current/index.html) | Documentation | Intermediate | Dashboards, Discover, and KQL query syntax |

---

## 🎥 Videos & Courses

| Resource | Type | Duration | Notes |
|----------|------|----------|-------|
| [ELK Stack Tutorial (TechWorld with Nana)](https://www.youtube.com/watch?v=4X0WLg05ASw) | Video | 1.5 hours | Best beginner ELK walkthrough |
| [Grafana Loki Crash Course (TechWorld with Nana)](https://www.youtube.com/watch?v=h_GGd7HfKQ8) | Video | 30 min | Loki + Promtail setup and LogQL basics |
| [Structured Logging Explained](https://www.youtube.com/watch?v=kO3cGK5MAr4) | Video | 15 min | Why JSON logging matters in production |
| [ELK vs Loki (DevOps Toolkit)](https://www.youtube.com/watch?v=VgHiE0YUKMU) | Video | 20 min | When to choose ELK vs Loki |
| [Centralized Logging (IBM Technology)](https://www.youtube.com/watch?v=7GJVx1okWfs) | Video | 10 min | Quick conceptual overview |

---

## 🧰 Tools & References

| Resource | Type | Notes |
|----------|------|-------|
| [Elasticsearch](https://www.elastic.co/elasticsearch/) | Tool | Distributed search and analytics engine |
| [Logstash](https://www.elastic.co/logstash/) | Tool | Log pipeline — ingest, transform, output |
| [Kibana](https://www.elastic.co/kibana/) | Tool | Visualization and search UI for Elasticsearch |
| [Filebeat](https://www.elastic.co/beats/filebeat) | Tool | Lightweight log shipper |
| [Grafana Loki](https://grafana.com/oss/loki/) | Tool | Log aggregation — like Prometheus but for logs |
| [Promtail](https://grafana.com/docs/loki/latest/send-data/promtail/) | Tool | Log shipper for Loki |
| [Fluentd](https://www.fluentd.org/) | Tool | Alternative log shipper (CNCF project) |
| [python-json-logger](https://github.com/madzak/python-json-logger) | Library | Structured JSON logging for Python |

---

## 🎯 Recommended Practice Path

1. **Week 1**: Set up Loki + Promtail + Grafana with Docker Compose. Ship app logs, learn LogQL. Build a log dashboard with error counts and patterns.
2. **Week 2**: Set up a minimal ELK stack with Docker Compose. Configure Filebeat → Logstash → Elasticsearch. Search logs in Kibana with KQL. Compare ELK vs Loki.
3. **Tool**: Add structured JSON logging to a project from a previous module and ship logs to Loki.
