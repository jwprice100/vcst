library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity ADDER is
generic (
    ADDER_WIDTH    : in positive
);
port (
    clock           : in std_logic;
    input_a         : in signed(ADDER_WIDTH-1 downto 0);
    input_b         : in signed(ADDER_WIDTH-1 downto 0);
    sum             : out signed(ADDER_WIDTH downto 0)
);
end entity ADDER;

architecture rtl of ADDER is
begin
    
    adder_proc: process(clock)
    begin
        if rising_edge(clock) then
            sum <= resize(input_a, ADDER_WIDTH+1) + resize(input_b, ADDER_WIDTH+1);
        end if;
    end process adder_proc;

end architecture rtl;