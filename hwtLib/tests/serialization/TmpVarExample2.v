module TmpVarExample2 (
    input wire[31:0] a,
    output reg[31:0] b
);
    always @(a) begin: assig_process_b
        reg[1:0] tmp_concat_0;
        reg[1:0] tmp_index_0;
        tmp_concat_0 = {a[31:16] == 16'h0001, a[15:0] == 16'h0001};
        tmp_index_0 = tmp_concat_0 + 2'b01;
        if (tmp_index_0[1] == 1'b0 & tmp_index_0[0] == 1'b0)
            b = 32'h00000000;
        else
            b = 32'h00000001;
    end

endmodule
