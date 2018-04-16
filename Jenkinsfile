pipeline {
  agent none
    environment {
      JENKINS_RUN = '1'
    }
  stages {
    stage('test') {
      parallel {
        stage('coverage') {
          agent {
            dockerfile {
              filename 'Dockerfile'
            }
          }
          steps {
            sh 'scripts/coverage.sh'
          }
          post {
            always {
              step([$class: 'XUnitBuilder',
                  thresholds: [
                  [$class: 'SkippedThreshold', failureThreshold: '0'],
                  [$class: 'FailedThreshold', failureThreshold: '0']],
                  tools: [[$class: 'CTestType', pattern: 'build-coverage/**/Test.xml']]])
              publishHTML (target: [
                  allowMissing: false,
                  alwaysLinkToLastBuild: false,
                  keepAll: true,
                  reportDir: 'build-coverage/coverage',
                  reportFiles: 'index.html',
                  reportName: 'Coverage Report'
              ])
            }
          }
        }
        stage('debian_pkg') {
          agent any
          environment {
            PKG_DESTDIR = 'build-ubuntu/pkg'
          }
          steps {
            // build package inside docker
            sh '''
               IMG_TAG=deb-$(cat /proc/sys/kernel/random/uuid)
               mkdir -p $PWD/$PKG_DESTDIR
               docker build -t ${IMG_TAG} -f Dockerfile.noostree .
               docker run -u $(id -u):$(id -g) -v $PWD:$PWD -v $PWD/${PKG_DESTDIR}:/persistent -w $PWD --rm ${IMG_TAG} $PWD/scripts/build-ubuntu.sh
               '''
            // test package installation in another docker
            sh 'scripts/test_aktualizr_deb_ubuntu.sh Dockerfile.noostree $PWD/$PKG_DESTDIR'
          }
        }
      }
    }
  }
}
// vim: set ft=groovy tabstop=2 shiftwidth=2 expandtab:
