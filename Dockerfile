FROM public.ecr.aws/unocha/python:3.12-stable

WORKDIR /srv

COPY . .

RUN --mount=source=.git,target=.git,type=bind \
    apk add --no-cache --upgrade --virtual .build-deps \
        build-base \
        git \
        libffi-dev \
        postgresql-dev \
        python3-dev \
        py3-wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir . && \
    apk del .build-deps && \
    apk add --no-cache libpq && \
    rm -rf /var/lib/apk/*

CMD python3 -m hapi.pipelines.app
