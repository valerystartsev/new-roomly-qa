FROM mcr.microsoft.com/playwright/java:v1.64.0-noble

WORKDIR /work/java
COPY java/pom.xml ./
RUN mvn -B -Dmaven.repo.local=/opt/maven-repository test-compile
COPY java/src ./src
RUN chmod -R a+rwX /work/java /opt/maven-repository
CMD ["mvn", "-B", "-Dmaven.repo.local=/opt/maven-repository", "test"]
