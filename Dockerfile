FROM ixsystems/catalog_validation

RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg
RUN echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null
RUN apt-get update

RUN apt-get install -y \
      skopeo    \
      git    \
      gh

ENV PYTHONUNBUFFERED 1
ENV WORK_DIR /app
RUN mkdir -p ${WORK_DIR}
WORKDIR ${WORK_DIR}

ADD . ${WORK_DIR}/
RUN git config --global --add safe.directory /catalog
RUN pip install -r requirements.txt
RUN pip install -U .
ENTRYPOINT ["catalog_update", "update", "-p", "--path", "/catalog/library/ix-dev"]
