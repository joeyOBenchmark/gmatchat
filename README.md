1. Create your .env file:
`cp .env.example .env`
then fill in the keys

2. Token permissions needed (one fine-grained PAT covering both repos):
- joeyOBenchmark/gmatbard — Contents: Read
- joeyOBenchmark/gmatchat — Contents: Read and write

3. Build and run:
docker compose build
docker compose up -d

The build clones gmatbard using the token as a BuildKit secret (never in image layers). At runtime, the entrypoint writes the token to git's credential store so git push works from inside the container.
