var temp = {
    type: 0,
    steps: 0,
    acList: {},
    touches: 0,
    addAddress: function (address) {
        if (address in this.acList) {
            return this.acList[address];
        }
        var slots = {};
        this.acList[address] = slots
        return slots;
    },
    addSlot: function (address, key) {
        var slots = this.addAddress(address)
        if (!(key in slots)) {
            slots[key] = ""
            this.acList[address] = slots
        }
    },
    result: function (ctx, db) {
        from = toHex(ctx['from'])
        this.addAddress(from)
        if (ctx['to']) {
            this.addAddress(toHex(ctx['to']))
        } else {
            // create contract
            this.type = 2
        }

        return {
            type: this.type,
            tt: this.touches,
            acl: this.acList
        }
    },
    fault: function (log, db) {
    },
    step: function (log, db) {
        this.type = 1
        if (log.getError()) {
            return
        }
        switch (log.op.toString()) {
            case "CALL":
            case "CALLCODE":
            case "DELEGATECALL":
            case "STATICCALL":
                this.addAddress(log.stack.peek(1).toString(16))
                this.touches = this.touches + 1;
                break;
            case "EXTCODECOPY":
            case "EXTCODESIZE":
            case "EXTCODEHASH":
            case "BALANCE":
            case "SELFDESTRUCT":
                this.addAddress(log.stack.peek(0).toString(16))
                this.touches = this.touches + 1;
                break;
            case "SLOAD":
                // case "SSTORE":
                this.addSlot(toHex(log.contract.getAddress()), log.stack.peek(1).toString(16))
                this.touches = this.touches + 1;
                break;
        }
        this.steps++;
    }
}
