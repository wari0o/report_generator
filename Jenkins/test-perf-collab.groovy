pipeline {
    agent {
        label 'editors-perf-tests'
    }

    parameters {
        string(name: 'SCRIPT_NAME', defaultValue: 'browser.js', description: 'Имя запускаемого скрипта')
        text(name: 'CONFIG_JSON', defaultValue: '''{
    "stand": "stand_address",
    "username": "username",
    "password": "password",
    "file_type": "doc",
    "file_uuid": "UUID",
    "sim_operation": "operation_name",
    "duration": "1m",
    "threads": 1,
    "sim_per_thread": 1
}''', description: 'Введите содержимое config.json')
        booleanParam(name: 'REPORT', defaultValue: false, description: 'Генерировать отчет в конфлюенс после теста?')
        password(name: 'CONFLUENCE_PAT', description: 'Confluence PAT token (требуется если REPORT=true)')
        string(name: 'CONFLUENCE_PARENT_ID', defaultValue: 'page_id', description: 'ID родительской страницы Confluence (требуется если REPORT=true)')
        string(name: 'CONFLUENCE_PAGE_NAME', defaultValue: 'Test report page', description: 'Название страницы отчета (требуется если REPORT=true)')
        booleanParam(name: 'COMPARE', defaultValue: false, description: 'Сравнивать с предыдущим отчетом?')
        string(name: 'COMPARE_PAGE_ID', defaultValue: '', description: 'ID предыдущей страницы для сравнения (если COMPARE=true)')
    }

    stages {
        stage('Checkout') {
            steps {
                git(
                    url: 'repo_url',
                    credentialsId: cred_id',
                    branch: 'master'
                )
            }
        }

        stage('Run Tests') {
            steps {
                script {
                    // Создание config.json
                    writeFile file: 'config.json', text: params.CONFIG_JSON
                    
                    // Запуск теста с замером времени
                    env.START_TIME = System.currentTimeMillis().toString()
                    
                    sh """
                    docker run \
                      -v "\$(pwd):/scripts" \
                      --rm \
                      --cpus="14" \
                      --memory="24g" \
                      --name k6 \
                      -e K6_INFLUXDB_ORGANIZATION="myorg" \
                      -e K6_INFLUXDB_BUCKET="k6" \
                      -e K6_INFLUXDB_TOKEN="my-super-secret-token" \
                      -e K6_INFLUXDB_ADDR="http://influxdb:8086" \
                      -i wari0o/xk6:influx_with_browser \
                      run "/scripts/${params.SCRIPT_NAME}" -o xk6-influxdb
                    """
                    
                    env.END_TIME = System.currentTimeMillis().toString()
                }
            }
        }

        stage('Generate Report') {
            when {
                expression { params.REPORT == true }
            }
            steps {
                script {
                    echo "Генерация отчета в Confluence..."
                    echo "START_TIME = ${env.START_TIME}"
                    echo "END_TIME = ${env.END_TIME}"
                    def comparePageIdArg = (params.COMPARE == true && params.COMPARE_PAGE_ID?.trim()) ? "--compare-page-id ${params.COMPARE_PAGE_ID}" : ""
                    sh """
                        cd report_gen
                        pip install -r requirements.txt
                        set +x
                        python main.py \
                          --start-time ${env.START_TIME} \
                          --end-time ${env.END_TIME} \
                          --confluence-pat "${params.CONFLUENCE_PAT}" \
                          --confluence-parent-id "${params.CONFLUENCE_PARENT_ID}" \
                          --confluence-page-name "${params.CONFLUENCE_PAGE_NAME}" \
                          --compare ${params.COMPARE} \
                          ${comparePageIdArg}
                        set -x
                    """
                }
            }
        }
    }

    post {
        always {
            echo "Pipeline завершен. Статус: ${currentBuild.result ?: 'SUCCESS'}"
            cleanWs() // Очистка workspace
        }
    }
}