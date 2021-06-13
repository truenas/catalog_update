FROM ixsystems/catalog_validation

RUN apt-get update

RUN apt-get install -y \
      skopeo

ENV PYTHONUNBUFFERED 1
ENV WORK_DIR /app
RUN mkdir -p ${WORK_DIR}
WORKDIR ${WORK_DIR}

ADD . ${WORK_DIR}/
RUN pip install -r requirements.txt
RUN pip install -U .
ENTRYPOINT ["catalog_update", "update", "-r", "--path"]
CMD ["/train"]
