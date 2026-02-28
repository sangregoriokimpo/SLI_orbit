import math
from dataclasses import dataclass
from typing import Tuple

Vec3 = Tuple[float, float, float]

def v_add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

def v_sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def v_mul(s:float, a: Vec3) -> Vec3:
    return (s * a[0], s* a[1], s* a[2])

def v_norm(a:Vec3) -> float:
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])

def _rot_z(a: float, v: Vec3) -> Vec3:
    c, s = math.cos(a), math.sin(a)
    x,y, z = v
    return (c*x - s*y, s*x + c*y,z)

def _rot_x(a: float, v:Vec3) -> Vec3:
    c, s = math.cos(a), math.sin(a)
    x,y,z = v
    return (x,c*y - s*z, s*y + c*z)

def _v_add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0]+b[0], a[1]+b[1], a[2]+b[2])

def _v_mul(s: float, v: Vec3) -> Vec3:
    return (s*v[0], s*v[1], s*v[2])

#CLASSICAL ORBITAL ELEMENTS TO WORLD VELOCITY AND POSITION
def C2RV(
    mu: float,
    a: float,
    e: float,
    inc: float,
    raan: float,
    argp: float,
    nu: float,
) -> tuple[Vec3, Vec3]:
    '''
    Orbital Elements -> Inertial/World Position & Velocity
    
    Inputs:
      mu   : m^3/s^2
      a    : meters
      e    : unitless
      inc  : radians
      raan : radians (Ω)
      argp : radians (ω)
      nu   : radians (true anomaly, θ)

    Returns:
      r_world (m), v_world (m/s)
    '''
    if a <= 0:
        raise ValueError("a must be > 0")
    if e < 0:
        raise ValueError("e must be >= 0")
    
    #SEMI LATUS RECTUM
    p = a * (1.0-e*e)

    #RADIUS
    r = p / (1.0 + e * math.cos(nu))
    
    #PERIFOCAL POSITION (PQW)
    r_pqw = (r * math.cos(nu), r* math.sin(nu),0.0)
    
    #PERIFOCAL VELOCITY
    #v = sqrt(mu/p) * [-sin(nu), e+cos(nu),0]
    fac = math.sqrt(mu/p)
    v_pqw = (-fac * math.sin(nu), fac* (e + math.cos(nu)), 0.0)

    #ROTATE PQW -> WORLD: Rz(raan) * Rx(inc) * rz(argp)
    r1= _rot_z(argp, r_pqw)
    r2 = _rot_x(inc, r1)
    r_world = _rot_z(raan,r2)
    v1 = _rot_z(argp, v_pqw)
    v2 = _rot_x(inc,v1)

    v1= _rot_z(argp,v_pqw)
    v2 = _rot_x(inc,v1)
    v_world = _rot_z(raan,v2)

    return r_world, v_world


#TWO BODY ORBIT
@dataclass
class TBO:
    mu: float
    center: Vec3 = (0.0,0.0,0.0)

    def accel(self, r: Vec3) -> Vec3:
        d = v_sub(r,self.center)
        rmag = v_norm(d)
        if rmag < 1e-12:
            return (0.0,0.0,0.0)
        return v_mul(-self.mu / (rmag ** 3), d)
    
    def rk4_step(self, r: Vec3, v: Vec3, dt:float) -> tuple[Vec3,Vec3]:
        #ONE RK4 STEP FOR:
        '''
        DR/DT = V
        DV/DT = A(R)
        '''

        a1 = self.accel(r)
        k1r, k1v = v, a1

        r2 = v_add(r,v_mul(0.5*dt, k1r))
        v2 = v_add(v,v_mul(0.5*dt, k1v))
        a2 = self.accel(r2)
        k2r, k2v = v2, a2

        r3 = v_add(r,v_mul(0.5*dt, k2r))
        v3 = v_add(v,v_mul(0.5*dt, k2v))
        a3 = self.accel(r3)
        k3r, k3v = v3, a3

        r4 = v_add(r,v_mul(dt, k3r))
        v4 = v_add(v,v_mul(dt, k3v))
        a4 = self.accel(r4)
        k4r, k4v = v4, a4

        r_next = v_add(
            r,
            v_mul(
                dt / 6.0,
                v_add(
                    v_add(k1r, v_mul(2.0, k2r)),
                    v_add(v_mul(2.0, k3r), k4r),
                ),
            ),
        )
        
        v_next = v_add(
            v,
            v_mul(
                dt / 6.0,
                v_add(
                    v_add(k1v, v_mul(2.0, k2v)),
                    v_add(v_mul(2.0, k3v), k4v),
                ),
            ),
        )

        return r_next, v_next
    
#INTEGRATOR CLOCK
@dataclass
class IC:
    '''
    FIXED STEP INTEGRATOR HELPER.
    - ACCUMULATES VARIABLE FRAME DT
    - ADVANCES THE INTEGRATOR IN FIXED DT_SIM STEPS
    '''

    dt_sim: float
    accum: float = 0.0

    def add_time(self,dt_frame: float) -> int:
        self.accum += dt_frame
        steps = int(self.accum // self.dt_sim)
        if steps > 0:
            self.accum -= steps * self.dt_sim
        return steps

#CIRCULAR ORBIT INTEGRATOR CLOCK
def COIC(mu: float, radius: float, plane: str = "xy") -> tuple[Vec3,Vec3]:
    '''
    CONVENIENCE INITIAL CONDITIONS FOR CIRCULAR ORBIT ABOUT ORIGIN
    PLANE: 'XY' , 'XZ' OR 'YZ'
    '''    

    v = math.sqrt(mu / radius)
    if plane == "xy":
        return (radius, 0.0,0.0), (0.0, v, 0.0)
    if plane == "xz":
        return (radius,0.0,0.0), (0.0, 0.0, v)
    if plane == "yz":
        return (0.0, radius ,0.0), (0.0, 0.0, v)
    raise ValueError("PLANE MUST BE xy, xz or yz")