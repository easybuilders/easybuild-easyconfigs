#!/usr/bin/env bash

if [ -z ${EB_CONFIG_DIR} ]; then
    echo "ERROR: EB_CONFIG_DIR is not set"
    exit 1
fi
if [ -z ${EBROOTRABBITMQ} ]; then
    echo "ERROR: Module RabbitMQ is not loaded"
    exit 1
fi
if [ -z ${EBROOTPOSTGRESQL} ]; then
    echo "ERROR: Module PostgreSQL is not loaded"
    exit 1
fi
if [ -z ${EBROOTAIIDAMINCORE} ]; then
    echo "ERROR: Module aiida-core is not loaded"
    exit 1
fi

echo "WARNING: this script will COMPLETELY and PERMANENTLYremove ALL data from the AiiDA database, repository and configuration."
read -p "Are you sure you want to continue? (Type \"Yes I am!\" to continue) " -r REPLY

if [[ "$REPLY" != "Yes I am!" ]]; then
    echo "Aborting."
    exit 1
fi

LOGHEADER="== "

AIIDA_LOGHEADER="${LOGHEADER}AiiDA:"
RMQ_LOGHEADER="${LOGHEADER}RabbitMQ:"
PG_LOGHEADER="${LOGHEADER}PostgreSQL:"

PGDATA="`cat $EB_CONFIG_DIR/psql_datadir`"
AIIDA_DIR="`cat ${EB_CONFIG_DIR}/aiida_dir`"

echo "${AIIDA_LOGHEADER} Stopping AiiDA daemon"
verdi daemon stop
echo "${RMQ_LOGHEADER} Stopping RabbitMQ"
rabbitmqctl stop 2> /dev/null
echo "${PG_LOGHEADER} Stopping PostgreSQL"
pg_ctl stop -D $PGDATA 2> /dev/null

echo "${AIIDA_LOGHEADER} Removing AiiDA database"
rm -rf $PGDATA
echo "${AIIDA_LOGHEADER} Removing AiiDA repository"
rm -rf $AIIDA_DIR
echo "${AIIDA_LOGHEADER} Removing the AiiDA configuration file"
rm -rf $HOME/.aiida
echo "${LOGHEADER} Removing the configuration folder"
rm -rf $EB_CONFIG_DIR
