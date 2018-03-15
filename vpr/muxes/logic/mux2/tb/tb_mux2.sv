`include "vunit_defines.svh"

module tb_mux2;

   logic I0;
   logic I1;
   logic S0;
   logic O;
   

   `TEST_SUITE begin

      `TEST_CASE("basic") begin
	 I0 = 1;
	 I1 = 0;
	 S0 = 0;
	 $display("before");
	 #(10);
	 $display("after");
	 `CHECK_EQUAL(O, 1);
	 S0 = 1;
	 #(10);
	 `CHECK_EQUAL(O, 0);
      end

   end

   MUX2 dut(I0,I1,S0,O);

endmodule // tb_mux2
