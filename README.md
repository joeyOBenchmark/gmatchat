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
```
docker compose build
docker compose up -d
```

The build clones gmatbard using the token as a BuildKit secret (never in image layers). At runtime, the entrypoint writes the token to git's credential store so git push works from inside the container.


5. Then open localhost:8080
  the first time you use it you will need to setup the account, and approve warnings but after that it should just open to the chat right away.






# TODO
 - the chat log should be saved to the repo.
 - there are a few issues the instances found.
     - we should cleanup the examples to all use the running, post processing, and the plotting.
     - then we could remove the test that blindly executes them.... but than maybe it will take forever.... idk... maybe the run, post, plot should be packaged into a simple tool.
 - You should be able to minimize the folders on the left.
 - claude complained that it couldnt auto update
 - we should convert all of the burns to finite burns.
 - we should number the simulation folders so that they are listed chronologically
 - we should have a better csv viewer
 - when you click on a file, the pop-up window should show the relative path
