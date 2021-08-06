FROM 819671467588.dkr.ecr.us-west-2.amazonaws.com/jenkins-leader:latest

# Install custom plugins
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN /usr/local/bin/install-plugins.sh < /usr/share/jenkins/ref/plugins.txt

COPY modify_casc.py /modify_casc.py
COPY config-as-code.j2 /config-as-code.j2

USER root

RUN apt-get update &&\
    apt-get install -y xvfb &&\
    apt-get install -y python-pip &&\
    apt-get install -y python3-pip &&\
    apt-get install -y awscli &&\
    apt-get install -y sloccount &&\
    pip install jinja2 dnspython virtualenv pylint radon coverage &&\
    pip3 install jinja2 dnspython virtualenv pylint radon coverage &&\
    rm -rf /var/lib/apt/lists/* &&\
    touch /config-as-code.yaml &&\
    chown jenkins: /config-as-code.yaml &&\
    sed -i '/\/bin\/bash*/a \\n\/modify_casc.py' /usr/local/bin/jenkins.sh

# User back to jenkins
USER jenkins
