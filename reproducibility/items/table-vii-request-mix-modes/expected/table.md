| mode | semantics | representative_run_id |
| --- | --- | --- |
| step | One request class is dominant for each segment while all other classes remain active at baseline weight. | continuous-longmix-scale45-step-steps500-20260611T120732Z |
| linear | Dominance shifts smoothly from the first request class to the last, with a midpoint bump for interior request classes. | continuous-longmix-scale45-linear-steps500-20260611T120733Z |
| sinusoidal | All request classes remain active while phase-shifted sinusoidal weights change the hot request over time. | continuous-longmix-scale45-sinusoidal-steps500-20260611T120734Z |
| markov | A Markov schedule changes the dominant request class stochastically while preserving nonzero baseline traffic for the rest. | continuous-longmix-scale45-markov-steps500-20260611T120735Z |
