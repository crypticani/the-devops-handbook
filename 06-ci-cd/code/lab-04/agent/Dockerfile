# A self-hosted Azure Pipelines agent.
#
# ⭐ Why self-hosted for a lab: a new Azure DevOps organisation gets ZERO Microsoft-hosted
# parallel jobs until you fill in a grant request form, which Microsoft answers in a few
# business days. Self-hosted parallelism is free and available immediately (1 job on the
# free tier), so this is the only way to run a pipeline today rather than next week.
#
# It is also what most enterprises actually run: agents inside their own network, where
# the build can reach a private registry, a licence server, or a database.
FROM ubuntu:22.04

ARG AGENT_VERSION=5.277.0
ENV DEBIAN_FRONTEND=noninteractive

# The agent needs a shell, git, and its own dependencies. Everything your *pipeline*
# needs must also be here — that is the trade of self-hosted: you own the toolchain.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git jq libicu70 sudo \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m agent && mkdir -p /azp && chown agent:agent /azp
USER agent
WORKDIR /azp

# Note the host: the older vstsagentpackage.azureedge.net CDN is being retired and
# already fails from some networks. download.agent.dev.azure.com is the current one.
RUN curl -fsSL -o agent.tar.gz \
      "https://download.agent.dev.azure.com/agent/${AGENT_VERSION}/vsts-agent-linux-x64-${AGENT_VERSION}.tar.gz" \
    && tar xzf agent.tar.gz \
    && rm agent.tar.gz

COPY --chown=agent:agent start.sh /azp/start.sh
ENTRYPOINT ["/azp/start.sh"]
