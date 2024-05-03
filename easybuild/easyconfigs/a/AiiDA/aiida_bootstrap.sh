#!/usr/bin/env bash

module load RabbitMQ
module load PostgreSQL
module load aiida-core

LOGHEADER="== "
PG_LOGHEADER="${LOGHEADER}PostgreSQL:"
EB_CONFIG_DIR=$HOME/.eb_aiida
export PGDATA=${EB_CONFIG_DIR}/TEST
PG_CONF=$PGDATA/postgresql.conf
PG_PORT=25432

function database_set_port {
    # Set the PG_port number
    while [ $PG_PORT -le 65535 ]; do
        ss -tln | grep -q ":$PG_PORT " || break
        PG_PORT=$((PG_PORT + 1))
    done
    if [ $PG_PORT -gt 65535 ]; then
        echo "${PG_LOGHEADER} no free PORT available"
        exit 1
    fi
    echo "${PG_LOGHEADER} setting PORT to $PG_PORT"
    sed -i "s/.*port = .*/port = ${PG_PORT}/" ${PG_CONF}
}

function database_get_set_port {
    # Get the PG_port number
    if [ "x`grep -e '# *port *= *' ${PG_CONF}`" != "x" ]; then
        echo "${PG_LOGHEADER} PORT not set"
        database_set_port
    else
        PG_PORT=$(grep '^port = ' ${PG_CONF} | awk '{print $3}')
        echo "${PG_LOGHEADER} Running on PORT $PG_PORT"
    fi
}

function database_get_set_pgdata {
    if [ -f ${EB_CONFIG_DIR}/psql_datadir ]; then
        PGDATA=$(cat ${EB_CONFIG_DIR}/psql_datadir)
    else
        echo "${PG_LOGHEADER} PGDATA not set"
        read -r -p "${PG_LOGHEADER} Enter PGDATA directory (default: $PGDATA): " _PGDATA
        if [ ! -z $_PGDATA ]; then
            PGDATA=$_PGDATA
        fi
        echo "${PG_LOGHEADER} Setting PGDATA to $PGDATA"
        echo $PGDATA > ${EB_CONFIG_DIR}/psql_datadir
    fi
}

function database_init {
    echo "${PG_LOGHEADER} Initializing database..."
    read -r -s -p "${PG_LOGHEADER} Enter the database (new) password: " PG_PASSWORD
    initdb -D ${PGDATA} -A scram-sha-256 --pwfile=<(echo ${PG_PASSWORD})
}

function database_start {
   # Check if postgresql is already running
    pg_ctl status -D $PGDATA 2>&1 > /dev/null
    if [ $? -ne 0 ]; then
        echo "${PG_LOGHEADER} starting server..."
        pg_ctl start -D ${PGDATA} -l ${PGDATA}/logfile
    else
        echo "${PG_LOGHEADER} server already running"
    fi
}

function database_bootstrap {
    if [ ! -d ${EB_CONFIG_DIR} ]; then
        mkdir -p ${EB_CONFIG_DIR}
    fi

    database_get_set_pgdata
    if [ ! -d ${PGDATA} ]; then
        database_init
    fi
    database_get_set_port
    database_start
}

# database_bootstrap
# if [ $? -ne 0 ]; then
#     echo "${PG_LOGHEADER} failed to start server"
#     exit 1
# fi
# echo "PASSWORD: $PG_PASSWORD"

RMQ_LOGHEADER="${LOGHEADER}RabbitMQ:"
RMQ_BASEDIR=${EB_CONFIG_DIR}/rabbitmq


export RABBITMQ_NODENAME=rabbit-${USER}
export RABBITMQ_MNESIA_BASE=${RMQ_BASEDIR}/mnesia
export RABBITMQ_LOG_BASE=${RMQ_BASEDIR}/logs
export RABBITMQ_CONFIG_FILES=${RMQ_BASEDIR}/config
export RABBITMQ_ADVANCED_CONFIG_FILE=${RMQ_BASEDIR}/advanced.config
export RABBITMQ_NODE_IP_ADDRESS="localhost"

function rabbitmq_set_port {
    _RMQ_PORT=25672
    while [ $_RMQ_PORT -le 65535 ]; do
        ss -tln | grep -q ":$_RMQ_PORT " || break
        _RMQ_PORT=$((_RMQ_PORT + 1))
    done
    if [ $_RMQ_PORT -gt 65535 ]; then
        echo "${RMQ_LOGHEADER} no free PORT available"
        exit 1
    fi
    export RABBITMQ_NODE_PORT=$_RMQ_PORT
    echo "${RMQ_LOGHEADER} Setting PORT to $RABBITMQ_NODE_PORT"
    echo $RABBITMQ_NODE_PORT > ${EB_CONFIG_DIR}/rmq_port
}

function rabbitmq_get_port {
    if [ -f ${EB_CONFIG_DIR}/rmq_port ]; then
        export RABBITMQ_NODE_PORT=$(cat ${EB_CONFIG_DIR}/rmq_port)
    fi
}

function rabbitmq_set_dist_port {
    _RMQ_PORT=25672
    while [ $_RMQ_PORT -le 65535 ]; do
        ss -tln | grep -q ":$_RMQ_PORT " || break
        _RMQ_PORT=$((_RMQ_PORT + 1))
    done
    if [ $_RMQ_PORT -gt 65535 ]; then
        echo "${RMQ_LOGHEADER} no free PORT available"
        exit 1
    fi
    export RABBITMQ_DIST_PORT=$_RMQ_PORT
    echo "${RMQ_LOGHEADER} Setting DIST_PORT to $RABBITMQ_DIST_PORT"
    echo $RABBITMQ_DIST_PORT > ${EB_CONFIG_DIR}/rmq_dist_port
}

function rabbitmq_get_dist_port {
    if [ -f ${EB_CONFIG_DIR}/rmq_dist_port ]; then
        export RABBITMQ_DISTPORT=$(cat ${EB_CONFIG_DIR}/rmq_port)
    fi
}

function rabbitmq_check_running {
    rabbitmqctl status | grep -q "RabbitMQ is running"
    if [ $? -ne 0 ]; then
        echo "${RMQ_LOGHEADER} server not running"
        return 1
    fi
    return 0



function rabbitmq_bootstrap {
    echo "${RMQ_LOGHEADER} starting server..."

    rabbitmq_get_port
    rabbitmq_get_dist_port

    rabbitmq-server -detached
    if [ $? -ne 0 ]; then
        echo "${RMQ_LOGHEADER} failed to start server"
        exit 1
    fi
}
