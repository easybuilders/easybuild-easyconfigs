.f90.o:
	$(FC) -c $(FFLAGS) $(INC) $<
.F90.o:
	$(FC) -c $(FFLAGS) $(INC) $<
.c.o:
	$(CC) -c $(CFLAGS) $(INC) $<
LUA_DIR = $(EBROOTLUA)
INC += -I$(LUA_DIR)/include
