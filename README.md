1. Create the GitHub repo and add the remote (do this once on the host, outside Docker):
# Create the repo on GitHub first (github.com/new), then:
git remote add origin https://github.com/joeyOBenchmark/gmatchat.git
git push -u origin main

2. Create your .env file:
cp .env.example .env
# then fill in the keys

3. Token permissions needed (one fine-grained PAT covering both repos):
- joeyOBenchmark/gmatbard — Contents: Read
- joeyOBenchmark/gmatchat — Contents: Read and write

4. Build and run:
docker compose build
docker compose up -d

The build clones gmatbard using the token as a BuildKit secret (never in image layers). At runtime, the entrypoint writes the token to git's credential store so git push works from inside the container.
