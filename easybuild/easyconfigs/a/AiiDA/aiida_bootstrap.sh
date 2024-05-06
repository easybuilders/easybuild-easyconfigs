#!/usr/bin/env bash

module load RabbitMQ
module load PostgreSQL
module load aiida-core

LOGHEADER="== "
EB_CONFIG_DIR=$HOME/.eb_aiida

#######################################################################
# PostgreSQL
#######################################################################
PG_LOGHEADER="${LOGHEADER}PostgreSQL:"
export PGDATA=${EB_CONFIG_DIR}/postgres
PG_CONF="${PGDATA}/postgresql.conf"
export PGHOST="${EB_CONFIG_DIR}"
export PGPORT=5432

function database_get_set_pgdata {
    if [ -f ${EB_CONFIG_DIR}/psql_datadir ]; then
        PGDATA=$(cat ${EB_CONFIG_DIR}/psql_datadir)
    else
        echo "${PG_LOGHEADER} PGDATA not set"
        read -r -p "${PG_LOGHEADER} Enter PGDATA directory (default: ${PGDATA}): " _PGDATA
        if [ ! -z ${_PGDATA} ]; then
            export PGDATA=${_PGDATA}
            PG_CONF="${PGDATA}/postgresql.conf"
        fi
        echo "${PG_LOGHEADER} Setting PGDATA to $PGDATA"
        echo "${PGDATA}" > ${EB_CONFIG_DIR}/psql_datadir
    fi
}

function database_get_password {
    if [ -f ${EB_CONFIG_DIR}/psql_password ]; then
        PG_PASSWORD=$(cat ${EB_CONFIG_DIR}/psql_password)
    fi
}

function database_get_set_password {
    if [ -f ${EB_CONFIG_DIR}/psql_password ]; then
        PG_PASSWORD=$(cat ${EB_CONFIG_DIR}/psql_password)
    else
        PG_PASSWORD="$(uuidgen)"
        echo $PG_PASSWORD > ${EB_CONFIG_DIR}/psql_password
        chmod 600 ${EB_CONFIG_DIR}/psql_password
    fi

}

function database_init {
    echo "${PG_LOGHEADER} Initializing database..."
    database_get_set_password
    initdb -D ${PGDATA} -A scram-sha-256 --pwfile=<(echo ${PG_PASSWORD}) 2>&1 > /dev/null
    # Configure PostgreSQL to use unix socket only
    sed -i "s/.*listen_addresses *= .*/listen_addresses = ''/" ${PG_CONF}
    sed -i "s:.*unix_socket_directories *= .*:unix_socket_directories = '${PGHOST}':" ${PG_CONF}
    sed -i "s/.*unix_socket_permissions *= .*/unix_socket_permissions = '0700'/" ${PG_CONF}
}

function database_bootstrap {
    echo "${PG_LOGHEADER} Bootstrapping..."
    if [ ! -d "${EB_CONFIG_DIR}" ]; then
        mkdir -p "${EB_CONFIG_DIR}"
    fi

    database_get_set_pgdata
    if [ ! -d "${PGDATA}" ]; then
        database_init
    fi

    pg_ctl status -D $PGDATA 2>&1 > /dev/null
    if [ $? -ne 0 ]; then
        echo "${PG_LOGHEADER} starting server..."
        pg_ctl start -D ${PGDATA} -l ${PGDATA}/logfile
    else
        echo "${PG_LOGHEADER} server already running"
    fi
}


#######################################################################
# RabbitMQ
#######################################################################
RMQ_LOGHEADER="${LOGHEADER}RabbitMQ:"
RMQ_BASEDIR=${EB_CONFIG_DIR}/rabbitmq


export RABBITMQ_NODENAME=rabbit-${USER}
export RABBITMQ_MNESIA_BASE=${RMQ_BASEDIR}/mnesia
export RABBITMQ_LOG_BASE=${RMQ_BASEDIR}/logs
export RABBITMQ_CONFIG_FILES=${RMQ_BASEDIR}/config
export RABBITMQ_ADVANCED_CONFIG_FILE=${RMQ_BASEDIR}/advanced.config
export RABBITMQ_DEFAULT_USER=aiida

function rabbitmq_set_port {
    if [ ! -z ${RABBITMQ_NODE_PORT} ]; then
        _RMQ_PORT=${RABBITMQ_NODE_PORT}
    else
        _RMQ_PORT=25672
    fi
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
    if [ ! -z ${RABBITMQ_DIST_PORT} ]; then
        _RMQ_PORT=${RABBITMQ_DIST_PORT}
        if [ $_RMQ_PORT -eq ${RABBITMQ_NODE_PORT} ]; then
            _RMQ_PORT=$((RABBITMQ_NODE_PORT + 1))
        fi
    else
        if [ ! -z ${RABBITMQ_NODE_PORT} ]; then
            _RMQ_PORT=$((RABBITMQ_NODE_PORT + 1))
        else
            _RMQ_PORT=25673
        fi
    fi
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
        export RABBITMQ_DIST_PORT=$(cat ${EB_CONFIG_DIR}/rmq_dist_port)
    fi
}

function rabbitmq_check_running {
    DATA=`rabbitmqctl status 2>&1`
    echo ${DATA} | grep -q "Node data directory: "
    if [ $? -ne 0 ]; then
        echo "${RMQ_LOGHEADER} server not running"
        return 1
    fi
    echo "${RMQ_LOGHEADER} server already running"
    echo "${DATA}" | grep -q "Node data directory: ${RABBITMQ_MNESIA_BASE}/${RABBITMQ_NODENAME}@${HOSTNAME}"
    if [ $? -ne 0 ]; then
        echo "${RMQ_LOGHEADER} server not running on correct data directory. Stopping..."
        rabbitmqctl stop 2> /dev/null
        return 1
    fi

    _PORT=`echo "${DATA}" | grep "amqp" | cut -d, -f2 | awk '{print $2}' | head -n 1`
    if [ ! -z ${RABBITMQ_NODE_PORT} ] && [ ${_PORT} -ne ${RABBITMQ_NODE_PORT} ]; then
        echo "${RMQ_LOGHEADER} server not running on correct PORT. Stopping..."
        rabbitmqctl stop 2> /dev/null
        return 1
    else
        export RABBITMQ_NODE_PORT=${_PORT}
        echo "${RMQ_LOGHEADER} server running on PORT ${RABBITMQ_NODE_PORT}"
        echo ${RABBITMQ_NODE_PORT} > ${EB_CONFIG_DIR}/rmq_port
    fi
    _DIST_PORT=`echo "$DATA" | grep "clustering" | cut -d, -f2 | awk '{print $2}' | head -n 1`
    if [ ! -z ${RABBITMQ_DIST_PORT} ] && [ ${_DIST_PORT} -ne ${RABBITMQ_DIST_PORT} ]; then
        echo "${RMQ_LOGHEADER} server not running on correct DIST_PORT. Stopping..."
        rabbitmqctl stop 2> /dev/null
        return 1
    else
        export RABBITMQ_DIST_PORT=${_DIST_PORT}
        echo "${RMQ_LOGHEADER} server running on DIST_PORT ${RABBITMQ_DIST_PORT}"
        echo ${RABBITMQ_DIST_PORT} > ${EB_CONFIG_DIR}/rmq_dist_port
    fi

    return 0
}

function rabbitmq_get_password {
    if [ -f ${EB_CONFIG_DIR}/rmq_password ]; then
        export RABBITMQ_DEFAULT_PASS=$(cat ${EB_CONFIG_DIR}/rmq_password)
    fi
}

function rabbitmq_get_set_password {
    if [ -f ${EB_CONFIG_DIR}/rmq_password ]; then
        export RABBITMQ_DEFAULT_PASS=$(cat ${EB_CONFIG_DIR}/rmq_password)
    else
        export RABBITMQ_DEFAULT_PASS=$(uuidgen)
        echo $RABBITMQ_DEFAULT_PASS > ${EB_CONFIG_DIR}/rmq_password
        chmod 600 ${EB_CONFIG_DIR}/rmq_password
    fi

}

function rabbitmq_aiida_config {
    if [ "`grep -c 'consumer_timeout, undefined' $RABBITMQ_ADVANCED_CONFIG_FILE 2>/dev/null`" == "" ]; then
        echo "Adding consumer_timeout to $RABBITMQ_ADVANCED_CONFIG_FILE"
        echo "[{rabbit, [{consumer_timeout, undefined}]}]." >> $RABBITMQ_ADVANCED_CONFIG_FILE
    fi
}

function rabbitmq_bootstrap {
    echo "${RMQ_LOGHEADER} Bootstrapping..."

    if [ ! -d ${RMQ_BASEDIR} ]; then
        echo "${RMQ_LOGHEADER} creating directories..."
        mkdir -p ${RABBITMQ_MNESIA_BASE}
        mkdir -p ${RABBITMQ_LOG_BASE}
        mkdir -p ${RABBITMQ_CONFIG_FILES}
    fi

    rabbitmq_get_port
    rabbitmq_get_dist_port

    rabbitmq_check_running
    if [ $? -eq 0 ]; then
        return 0
    fi

    rabbitmq_set_port
    rabbitmq_set_dist_port
    rabbitmq_get_set_password

    rabbitmq_aiida_config

    echo "${RMQ_LOGHEADER} starting server..."
    rabbitmq-server -detached
    if [ $? -ne 0 ]; then
        echo "${RMQ_LOGHEADER} failed to start server"
        exit 1
    fi
}

#######################################################################
# AiiDA
#######################################################################
AIIDA_LOGHEADER="${LOGHEADER}AiiDA:"

export AIIDA_PATH=${HOME}
AIIDA_CONFIG_FILE=${AIIDA_PATH}/.aiida/config.json

function aiida_create_profile {
    read -r -p "${AIIDA_LOGHEADER} Enter email address (default to ${USER}@${HOSTNAME}.xz): " AIIDA_EMAIL
    if [ -z ${AIIDA_EMAIL} ]; then
        AIIDA_EMAIL=${USER}@${HOSTNAME}.xz
    fi
    read -r -p "${AIIDA_LOGHEADER} Enter first name (default to ${USER}): " AIIDA_FIRSTNAME
    if [ -z ${AIIDA_FIRSTNAME} ]; then
        AIIDA_FIRSTNAME=${USER}
    fi
    read -r -p "${AIIDA_LOGHEADER} Enter last name (default to ${USER}): " AIIDA_LASTNAME
    if [ -z ${AIIDA_LASTNAME} ]; then
        AIIDA_LASTNAME=${USER}
    fi
    read -r -p "${AIIDA_LOGHEADER} Enter institution (default to ${HOSTNAME}): " AIIDA_INSTITUTION
    if [ -z ${AIIDA_INSTITUTION} ]; then
        AIIDA_INSTITUTION=${HOSTNAME}
    fi
    read -r -p "${AIIDA_LOGHEADER} Enter data repository directory (default to ${EB_CONFIG_DIR}/aiida): " AIIDA_DIR
    if [ -z ${AIIDA_DIR} ]; then
        AIIDA_DIR=${EB_CONFIG_DIR}/aiida
        echo "${AIIDA_DIR}" > ${EB_CONFIG_DIR}/aiida_dir
    fi

    database_get_password
    rabbitmq_get_password

    echo "${AIIDA_LOGHEADER} Creating profile..."
    verdi quicksetup \
        --non-interactive \
        --profile ${USER} \
        --email ${AIIDA_EMAIL} \
        --first-name ${AIIDA_FIRSTNAME} \
        --last-name ${AIIDA_LASTNAME} \
        --institution ${AIIDA_INSTITUTION} \
        --su-db-name postgres \
        --su-db-username ${USER} \
        --su-db-password ${PG_PASSWORD} \
        --broker-port ${RABBITMQ_NODE_PORT} \
        --broker-username ${RABBITMQ_DEFAULT_USER} \
        --broker-password ${RABBITMQ_DEFAULT_PASS}

    if [ $? -ne 0 ]; then
        echo "${AIIDA_LOGHEADER} failed to create profile"
        exit 1
    fi
}

function aiida_verify_rmq_port {
    _AIIDA_PORT=$(verdi profile show ${USER} | grep "broker_port" | awk '{print $2}')
    if [ $_AIIDA_PORT -ne $RABBITMQ_NODE_PORT ]; then
        echo "${AIIDA_LOGHEADER} AiiDA RabbitMQ PORT mismatch, updating the profile..."
        sed -i "s/: *${_AIIDA_PORT}/: ${RABBITMQ_NODE_PORT}/" ${AIIDA_CONFIG_FILE}
    fi
}

function aiida_verify_rabbitmq {
    if [ "rabbitmqctl environment | grep consumer_timeout | grep undefined" != "" ]; then
        echo "${AIIDA_LOGHEADER} consumer_timeout was properly set in RabbitMQ, disabling warnings..."
        verdi config set warnings.rabbitmq_version false
    else
        echo "${AIIDA_LOGHEADER} consumer_timeout was wrongly set in RabbitMQ"
        echo "${AIIDA_LOGHEADER}   Manually kill the RabbitMQ server and relaunch the bootstrap script"
        exit 1
    fi
}

function aiida_start_daemon {
    if [ "`verdi daemon status 2>&1 | grep 'not running'`" != "" ]; then
        echo "${AIIDA_LOGHEADER} Starting AiiDA Daemon..."
        verdi daemon start
    else
        echo "${AIIDA_LOGHEADER} AiiDA Daemon already running"
    fi
}

function aiida_bootstrap {
    echo "${AIIDA_LOGHEADER} Bootstrapping..."

    if [ "`verdi profile list 2>&1 | grep 'no profiles'`" != "" ]; then
        aiida_create_profile
    fi

    aiida_verify_rabbitmq
    aiida_verify_rmq_port

    aiida_start_daemon
}

database_bootstrap
if [ $? -ne 0 ]; then
    echo "${PG_LOGHEADER} failed to start server"
    exit 1
fi
echo ""

rabbitmq_bootstrap
if [ $? -ne 0 ]; then
    echo "${RMQ_LOGHEADER} failed to start server"
    exit 1
fi
echo ""

# exit 0
aiida_bootstrap
if [ $? -ne 0 ]; then
    echo "${AIIDA_LOGHEADER} failed to start server"
    exit 1
fi
echo "AiiDA is ready to use"
