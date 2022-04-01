## Geth Trace Helper 

A simple helper tool to trace Ethereum transactions with two customized javascript tracers.
* dis_tracer is extracted from go-ethereum and modified to disassemble a transaction
* ac_tracer is used to record storage access list of a transaction ( except SSTORE )
* ac_tracer2 is similar with ac_tracer, but the result is organized together with contract calls. A -s parameter will produce the same format output as ac_tracer. 