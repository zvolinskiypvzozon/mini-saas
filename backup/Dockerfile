# mc (клиент S3) берём из образа хранилища, pg_dump/pg_restore — из postgres той же версии, что и БД
FROM pgsty/silo:latest AS mc

FROM postgres:16
COPY --from=mc /usr/bin/mc /usr/local/bin/mc
COPY common.sh backup.sh restore.sh verify.sh entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/*.sh
ENTRYPOINT ["entrypoint.sh"]
