library ieee;
use     ieee.std_logic_1164.all;
use     ieee.numeric_std.all;


entity Counter is
	generic (
		BITS : positive := 4
	);
	port (
		Clock  : in  std_logic;
		Reset  : in  std_logic;
		Enable : in  std_logic;
		Mode   : in  std_logic_vector(1 downto 0);
		Value  : out unsigned(BITS - 1 downto 0);
		Wrap   : out std_logic
	);
end entity;


architecture rtl of Counter is
	type T_State is (Idle, Counting, Holding);

	signal State : T_State := Idle;
	signal Count : unsigned(BITS - 1 downto 0) := (others => '0');
begin
	Sequential: process(Clock)
	begin
		if rising_edge(Clock) then
			if Reset = '1' then
				State <= Idle;  Count <= (others => '0');
			elsif Enable = '1' and Mode /= "11" then
				State <= Counting;
				case Mode is
					when "00" =>
						Count <= Count + 1;
					when "01" =>
						Count <= Count - 1;
					when others =>
						Count <= Count + 2;
				end case;
			else
				State <= Holding;
			end if;
		end if;
	end process;

	Value <= Count;
	Wrap  <= '1' when Count = (Count'range => '1') else
	         'Z' when State = Holding else
	         '0';

	-- psl default clock is rising_edge(Clock);
	-- psl WrapSeen: cover {Wrap = '1'};

	Overflow: process
	begin
		wait until Count = (Count'range => '1') and Mode = "10";
		report "Counter overflows by 2." severity warning;
	end process;
end architecture;
