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




Thrust       dv1       dv2       dv3     arc1     arc2     arc3  int1_alt  int2_alt
         22,000     501.3     710.5    1181.2     24.0     23.0     19.4  2516km   7415km
         15,000     480.4     684.9    1227.7     33.9     33.2     30.7  2412km   6987km
         10,000     467.4     669.8    1255.8     49.6     49.2     48.2  2348km   6738km
          8,000     464.2     666.1    1262.7     61.6     61.4     60.9  2332km   6678km
          6,000     462.6     664.3    1266.1     81.8     81.8     81.6  2324km   6648km





All four passes converged cleanly. Here's the full picture now with finite burns in the comparison:

  ┌─────────────────┬────────┬──────────────────┬────────────┬──────────────┐
  │     Config      │ Thrust │       Arcs       │ Propellant │ Gravity loss │
  ├─────────────────┼────────┼──────────────────┼────────────┼──────────────┤
  │ Impulsive (any) │ any    │ —                │ 11,799 kg  │ baseline     │
  ├─────────────────┼────────┼──────────────────┼────────────┼──────────────┤
  │ Finite Hohmann  │ 22 kN  │ ~92° (1 pass)    │ 11,919 kg  │ +120 kg      │
  ├─────────────────┼────────┼──────────────────┼────────────┼──────────────┤
  │ Finite 4-stage  │ 4 kN   │ ~92° (4 passes)  │ 12,044 kg  │ +246 kg      │
  ├─────────────────┼────────┼──────────────────┼────────────┼──────────────┤
  │ Finite 4-stage  │ 3 kN   │ ~117° (4 passes) │ 12,171 kg  │ +372 kg      │
  └─────────────────┴────────┴──────────────────┴────────────┴──────────────┘


1.14days for 4kn

0.38 days for 22kn
