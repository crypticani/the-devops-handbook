# Module 07: Observability — Resources

---

## 📖 Essential Reading

| Resource | Type | Difficulty | Notes |
|----------|------|------------|-------|
| [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/) | Documentation | Beginner | Official guide — start with "Getting Started" |
| [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/) | Reference | Intermediate | **Bookmark this** — essential query patterns |
| [Grafana Documentation](https://grafana.com/docs/grafana/latest/) | Documentation | Beginner | Dashboard creation, data sources, alerting |
| [Google SRE Book — Ch. 6: Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/) | Book (Free) | Intermediate | The Four Golden Signals — foundational reading |
| [Observability Engineering (Majors, Fong-Jones, Miranda)](https://www.oreilly.com/library/view/observability-engineering/9781492076438/) | Book | Advanced | Modern observability philosophy and practices |

---

## 🎥 Videos & Courses

| Resource | Type | Duration | Notes |
|----------|------|----------|-------|
| [Prometheus Tutorial (TechWorld with Nana)](https://www.youtube.com/watch?v=QoDqxm7ybLc) | Video | 1 hour | Best beginner Prometheus walkthrough |
| [Prometheus & Grafana (That DevOps Guy)](https://www.youtube.com/watch?v=h4Sl21AKiDg) | Video | 30 min | Practical setup with Docker Compose |
| [PromQL for Beginners (Julius Volz)](https://www.youtube.com/watch?v=hvACEDjHQZE) | Video | 45 min | PromQL from Prometheus co-founder |
| [Monitoring vs Observability (IBM Technology)](https://www.youtube.com/watch?v=b4K3-4Iw_Lk) | Video | 8 min | Quick conceptual overview for interviews |
| [Four Golden Signals (Google Cloud)](https://www.youtube.com/watch?v=5LMz7JQAGLE) | Video | 15 min | Google SRE concepts explained simply |

---

## 🧰 Tools & References

| Resource | Type | Notes |
|----------|------|-------|
| [Prometheus](https://prometheus.io/) | Tool | Time-series metrics collection and alerting |
| [Grafana](https://grafana.com/grafana/) | Tool | Visualization and dashboarding |
| [Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/) | Tool | Alert routing, grouping, and notification |
| [Node Exporter](https://github.com/prometheus/node_exporter) | Exporter | Linux host metrics (CPU, memory, disk, network) |
| [cAdvisor](https://github.com/google/cadvisor) | Exporter | Container resource usage metrics |
| [Awesome Prometheus Alerts](https://awesome-prometheus-alerts.grep.to/) | Reference | Collection of ready-to-use alerting rules |
| [Grafana Dashboard Library](https://grafana.com/grafana/dashboards/) | Registry | Community-built dashboards (import by ID) |
| [PromLens](https://promlens.com/) | Tool | Visual PromQL query builder and explainer |

---

## 🎯 Recommended Practice Path

1. **Week 1**: Set up Prometheus + Grafana + Node Exporter with Docker Compose. Explore PromQL queries in the Prometheus UI. Build a system dashboard in Grafana.
2. **Week 2**: Instrument a Python/Node app with Prometheus client. Create custom metrics (RED). Configure alert rules and Alertmanager. Trigger and resolve alerts.
3. **Tool**: Import a community Grafana dashboard (e.g., Node Exporter Full, ID: 1860) and study its PromQL queries.
