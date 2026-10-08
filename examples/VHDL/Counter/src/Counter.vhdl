library ieee;
use     ieee.std_logic_1164.all;
use     ieee.numeric_std.all;


entity Counter is
	generic (
		BITS : positive := 8
	);
	port (
		Clock  : in  std_logic;
		Reset  : in  std_logic;
		Enable : in  std_logic;
		Value  : out unsigned(BITS - 1 downto 0);
		Wrap   : out std_logic
	);
end entity;


architecture rtl of Counter is
	signal Count : unsigned(BITS - 1 downto 0) := (others => '0');
begin
	process(Clock)
	begin
		if rising_edge(Clock) then
			if Reset = '1' then
				Count <= (others => '0');
			elsif Enable = '1' then
				Count <= Count + 1;
			end if;
		end if;
	end process;

	Value <= Count;
	Wrap  <= '1' when Count = (Count'range => '1') else '0';
end architecture;
