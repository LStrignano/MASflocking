Bitcoin Market ABM — NetLogo

An agent-based model (ABM) of a simplified Bitcoin market, developed in NetLogo.

The project is currently in an experimental/development stage. The main goal is to build and validate the agent dynamics first, before introducing real market data and eventually allowing the simulated trading activity to influence the simulated Bitcoin price.

Project idea

The model represents a market populated by three different types of agents:

Agents A — Trend Followers

Tend to follow the current market direction.

Positive returns push them upward.

Negative returns push them downward.

Agents B — Contrarians

Tend to move against the current market direction.

Positive returns push them downward.

Negative returns push them upward.

Agents C — Fundamentalists

Have no direct directional bias from market returns.

Currently remain closer to the central region of the model.

Their future behaviour can be extended with fundamental/value signals.

The agents move around the NetLogo world and interact through:

intra-species flocking;

inter-species repulsion;

market-dependent movement;

probabilistic Bitcoin trading;

individual Bitcoin holdings;

individual cash balances.

The intention is to investigate whether these simple heterogeneous behaviours can produce meaningful aggregate market dynamics.

Current model architecture

At the moment, the model uses synthetic Bitcoin price data rather than real market data.

Several scenarios can be generated:

bull-market

bear-market

sideways

crash

bubble

These scenarios generate a sequence of artificial prices and returns.

The model then uses:

price
  ↓
return
  ↓
volatility
  ↓
agent movement
  ↓
agent position
  ↓
buy / sell probability
  ↓
simulated trading volume


The current model therefore uses price as an input to the agent system.

The longer-term objective is to eventually investigate the reverse relationship:

agent behaviour
      ↓
trading activity
      ↓
modelled volume
      ↓
price dynamics
      ↓
new return
      ↓
new agent behaviour


This would turn the model into a more genuinely endogenous market simulation.

Current outputs

The model currently tracks several quantities.

Market variables

Bitcoin price

Bitcoin return

Bitcoin volatility

simulated trading volume

simulated trading volume in USD

Portfolio variables

Bitcoin held by each agent

cash held by each agent

total Bitcoin

total cash

total wealth

Bitcoin held by each breed

Collective behaviour

global order parameter

order parameter for each agent population

mean Y-position of Agents A

mean Y-position of Agents B

phase correlation between A and B

heterogeneity index

instability/absorption parameter (lambda)

Some of these metrics are currently calculated internally but are not necessarily plotted.

Running the model

Open the .nlogo file in NetLogo.

Before pressing go, configure the model parameters in the Interface tab.

Important parameters include things such as:

population-a

population-b

population-c

spawn-radius

vision

repulsion-radius

repulsion-strength

temperature

k

h

trade-size

trade-interval

num-days

window-size

scenario

Then:

Press Setup.

Select a scenario.

Press Go.

Observe the agent dynamics and plots.

Compare the resulting trading volume and collective behaviour between scenarios.

Agent movement

Agent movement is influenced by two components.

X component

The X component is shared by all breeds:

X movement = k × volatility


Higher volatility therefore pushes agents farther away from the centre.

Y component

The Y component depends on the agent type.

Trend followers:

Y movement = h × return


Contrarians:

Y movement = -h × return


Fundamentalists:

Y movement = 0


This creates a simple spatial representation of different trading philosophies.

Trading mechanism

Trading probability is currently determined by the agent's X-position.

Agents farther toward the trading side of the world have a higher probability of participating in a trade.

The Y-position determines whether the agent:

buys when y >= 0

sells when y < 0

The amount traded is limited by:

available cash for purchases;

available Bitcoin for sales;

trade-size.

The model currently records the number of Bitcoin traded and converts this to USD volume using the current simulated Bitcoin price.

Synthetic market scenarios

Synthetic data is currently used deliberately.

This allows the model mechanics to be tested without depending on external APIs or datasets.

Bull market

Positive drift with moderate noise.

Bear market

Negative drift with moderate noise.

Sideways

Approximately zero drift with lower volatility.

Crash

A relatively stable period followed by a sudden large decline.

Bubble

The price goes through several phases:

growth
  ↓
euphoria
  ↓
violent collapse
  ↓
post-bubble stabilization


These scenarios are mainly intended as controlled experiments rather than realistic Bitcoin price models.

Current development philosophy

The project is being developed in stages.

Stage 1 — Make the model work

Get the NetLogo model running reliably.

Validate:

setup;

agent movement;

trading;

portfolio accounting;

volume calculation;

plots;

model metrics.

Stage 2 — Test synthetic scenarios

Run repeated experiments under different market conditions.

Questions to investigate:

Does volume respond consistently to volatility?

Do different agent populations produce different volume patterns?

Does heterogeneity affect collective behaviour?

Do crashes and bubbles generate distinctive agent dynamics?

Are the results reproducible across random seeds?

Stage 3 — Introduce real market data

Replace the synthetic price generator with historical Bitcoin data.

Potential inputs:

price;

returns;

volatility;

real trading volume;

potentially other market variables later.

The synthetic scenarios should remain available for controlled experiments.

Stage 4 — Validate the model

Compare simulated behaviour against historical Bitcoin data.

The main target is currently volume.

The idea is to determine whether the model can reproduce useful properties of observed trading volume before attempting to make price endogenous.

Stage 5 — Endogenize price

If the volume dynamics prove useful, the next major step is to allow simulated trading activity to influence price.

Conceptually:

agent behaviour
      ↓
buy/sell imbalance
      ↓
trading volume
      ↓
price impact
      ↓
new Bitcoin price
      ↓
new return
      ↓
agent behaviour


This would create a feedback loop between the agents and the market.

Repository structure

A possible repository structure:

bitcoin-market-abm/
│
├── README.md
├── LICENSE
├── .gitignore
│
├── model/
│   └── bitcoin-market.nlogo
│
├── data/
│   ├── raw/
│   └── processed/
│
├── results/
│   ├── plots/
│   └── experiments/
│
├── docs/
│   └── notes/
│
└── experiments/
    └── experiment-notes.md


At the current stage, the most important file is simply the .nlogo model.

The other folders can be introduced as the project grows.

Git / GitHub workflow

The repository is intended to make development easier and keep a history of changes.

Basic workflow:

git status
git add .
git commit -m "Describe the change"
git push


Before making larger changes:

git status
git log --oneline


Useful idea: commit whenever the model reaches a working state.

For example:

"Restore working model"
"Add bubble scenario"
"Fix trading volume calculation"
"Add order parameter"
"Disable stability plots"
"Add real BTC dataset"


This makes it possible to return to an earlier working version when experimentation inevitably breaks something.

Important current limitations

This is not yet intended to be a realistic Bitcoin market simulator.

Current simplifications include:

synthetic price generation;

simplified trading rules;

no order book;

no bid/ask spread;

no transaction costs;

no liquidity constraints;

no external market participants;

no endogenous price formation;

simplified fundamentalist behaviour;

simplified relationship between spatial position and trading behaviour.

These are intentional for now.

The first objective is to understand whether the agent mechanism itself produces useful aggregate behaviour.

Main research question

A working version of the project can be thought of as asking:

Can heterogeneous agent behaviour generate realistic patterns in aggregate trading volume?

Only after answering that question should the model attempt to use its simulated trading activity to generate price dynamics.

Status

Current status: Prototype / working development model

The model currently:

 runs in NetLogo

 contains three heterogeneous agent populations

 generates synthetic market scenarios

 simulates Bitcoin holdings and cash

 simulates buying and selling

 calculates model trading volume

 calculates several collective-behaviour metrics

 plots basic price, volume and order-parameter information

 import historical Bitcoin data

 validate simulated volume against real volume

 calibrate model parameters

 perform systematic experiments

 develop endogenous price dynamics

 validate the complete feedback system

Notes

This README is intentionally provisional.

The model is expected to change significantly as experiments reveal which mechanisms are useful and which are not.

Keep this document updated when major architectural decisions are made.