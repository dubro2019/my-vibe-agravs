FROM cimg/android:2024.04-node

WORKDIR /app

# コンテナ内のNode.jsをバージョン22にアップデート
RUN sudo npm install -g n && sudo n 22

COPY package.json ./
RUN npm install

COPY . .

# 【ここを修正】コピーしたファイルの所有権を、コンテナを実行するユーザー(circleci)に変更して書き込み権限を与える
RUN sudo chown -R circleci:circleci /app

RUN npx cap add android || true
RUN npx cap sync

WORKDIR /app/android
CMD ["./gradlew", "assembleDebug"]
