pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 15, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '15'))
    }

    environment {
        IMAGE_NAME = 'nexus-devops'
        CONTAINER_NAME = 'nexus-devops'
        APP_PORT = '5000'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install') {
            steps {
                bat '''
                    if not exist .venv python -m venv .venv
                    .venv\\Scripts\\python.exe -m pip install --upgrade pip
                    .venv\\Scripts\\python.exe -m pip install -r requirements.txt
                    if not exist reports mkdir reports
                '''
            }
        }

        stage('Test') {
            parallel {
                stage('Application Tests') {
                    steps {
                        bat '''
                            if not exist reports mkdir reports
                            .venv\\Scripts\\python.exe -m pytest tests\\test_app.py --junitxml=reports\\application-tests.xml
                        '''
                    }
                }
                stage('Jenkins Integration Tests') {
                    steps {
                        bat '''
                            if not exist reports mkdir reports
                            .venv\\Scripts\\python.exe -m pytest tests\\test_jenkins_config.py --junitxml=reports\\jenkins-tests.xml
                        '''
                    }
                }
            }
        }

        stage('Docker Build') {
            steps {
                bat '''
                    docker build -t %IMAGE_NAME%:%BUILD_NUMBER% -t %IMAGE_NAME%:latest --label com.nexus.jenkins.build=%BUILD_NUMBER% --label com.nexus.git.commit=%GIT_COMMIT% .
                '''
            }
        }

        stage('Deploy') {
            steps {
                bat '''
                    docker rm -f %CONTAINER_NAME% 2>NUL || exit /b 0
                    docker run -d --name %CONTAINER_NAME% -p %APP_PORT%:5000 --restart unless-stopped %IMAGE_NAME%:%BUILD_NUMBER%
                '''
            }
        }

        stage('Health Check') {
            steps {
                bat '''
                    powershell -NoProfile -Command "$ok=$false; for($i=1;$i -le 15;$i++){ try { $r=Invoke-WebRequest -UseBasicParsing http://127.0.0.1:%APP_PORT%/health -TimeoutSec 3; if($r.StatusCode -eq 200){$ok=$true; break} } catch {}; Start-Sleep -Seconds 2 }; if(-not $ok){ docker logs %CONTAINER_NAME%; exit 1 }; Write-Host 'Health check PASSED.'"
                '''
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: 'reports/*.xml'
        }
        success {
            echo "NEXUS CI/CD pipeline completed successfully. Build #${BUILD_NUMBER}"
        }
        failure {
            echo "NEXUS pipeline failed. Use the real Jenkins console with the AI RCA workflow."
        }
        cleanup {
            bat '''
                docker image prune -f
                if exist .venv rmdir /s /q .venv
            '''
        }
    }
}
