"""
sm_bridge.py — Adaptadores leves que conectam RF2Info (Shared Memory)
à interface esperada pelo TelemetryReader.

Substitui rf2_data.py (que depende de módulos externos do TinyPedal)
por wrappers diretos sobre a API de Shared Memory.
"""

from __future__ import annotations

import math
import logging

from adapter.rf2_connector import RF2Info

logger = logging.getLogger("LMU_VE.sm_bridge")


def _safe(val: float) -> float:
    """Retorna 0.0 se val for inf ou nan."""
    if math.isnan(val) or math.isinf(val):
        return 0.0
    return val


def _bytes_to_str(raw: bytes) -> str:
    """Converte bytes C para string Python."""
    try:
        return raw.decode("iso-8859-1").rstrip("\x00").strip()
    except Exception:
        return ""


def _vel2speed(vx: float, vy: float, vz: float) -> float:
    """Calcula velocidade (m/s) a partir dos componentes de velocidade local."""
    return math.sqrt(vx * vx + vy * vy + vz * vz)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Adaptadores individuais — mesma interface que
# TelemetryReader.connect() espera
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SMSession:
    """Proxy de sessão sobre RF2Info."""

    def __init__(self, shmm: RF2Info):
        self._s = shmm

    def track_name(self) -> str:
        return _bytes_to_str(self._s.rf2ScorInfo.mTrackName)

    def track_temperature(self) -> float:
        return _safe(self._s.rf2ScorInfo.mTrackTemp)

    def ambient_temperature(self) -> float:
        return _safe(self._s.rf2ScorInfo.mAmbientTemp)

    def raininess(self) -> float:
        return _safe(self._s.rf2ScorInfo.mRaining)

    def session_type(self) -> int:
        session = self._s.rf2ScorInfo.mSession
        if session >= 10:
            return 4  # race
        if session == 9:
            return 3  # warmup
        if session >= 5:
            return 2  # qualify
        if session >= 1:
            return 1  # practice
        return 0  # test day

    # ── Dados de Clima (para geração de setups) ──

    def dark_cloud(self) -> float:
        """Nível de nuvens escuras (0.0-1.0). Indica probabilidade de chuva."""
        return _safe(self._s.rf2ScorInfo.mDarkCloud)

    def wind(self) -> tuple[float, float, float]:
        """Velocidade do vento (x, y, z) em m/s."""
        w = self._s.rf2ScorInfo.mWind
        return (_safe(w.x), _safe(w.y), _safe(w.z))

    def min_path_wetness(self) -> float:
        """Nível mínimo de umidade da pista (0.0-1.0)."""
        return _safe(self._s.rf2ScorInfo.mMinPathWetness)

    def max_path_wetness(self) -> float:
        """Nível máximo de umidade da pista (0.0-1.0)."""
        return _safe(self._s.rf2ScorInfo.mMaxPathWetness)

    def avg_path_wetness(self) -> float:
        """Nível médio de umidade da pista (0.0-1.0)."""
        return _safe(self._s.rf2ScorInfo.mAvgPathWetness)

    def wind_speed(self) -> float:
        """Velocidade do vento (m/s)."""
        w = self._s.rf2ScorInfo.mWind
        return math.sqrt(_safe(w.x)**2 + _safe(w.y)**2 + _safe(w.z)**2)


class SMVehicle:
    """Proxy de veículo sobre RF2Info."""

    def __init__(self, shmm: RF2Info):
        self._s = shmm

    def vehicle_name(self) -> str:
        return _bytes_to_str(self._s.rf2ScorVeh().mVehicleName)

    def class_name(self) -> str:
        return _bytes_to_str(self._s.rf2ScorVeh().mVehicleClass)

    def speed(self) -> float:
        vel = self._s.rf2TeleVeh().mLocalVel
        return _safe(_vel2speed(vel.x, vel.y, vel.z))

    def fuel(self) -> float:
        return _safe(self._s.rf2TeleVeh().mFuel)

    def in_pits(self) -> bool:
        return bool(self._s.rf2ScorVeh().mInPits)

    def in_garage(self) -> bool:
        return bool(self._s.rf2ScorVeh().mInGarageStall)

    def position_vertical(self) -> float:
        return _safe(self._s.rf2TeleVeh().mPos.y)

    def downforce_front(self) -> float:
        return _safe(self._s.rf2TeleVeh().mFrontDownforce)

    def downforce_rear(self) -> float:
        return _safe(self._s.rf2TeleVeh().mRearDownforce)

    def accel_longitudinal(self) -> float:
        return _safe(self._s.rf2TeleVeh().mLocalAccel.z)

    def accel_lateral(self) -> float:
        return _safe(self._s.rf2TeleVeh().mLocalAccel.x)

    def accel_vertical(self) -> float:
        return _safe(self._s.rf2TeleVeh().mLocalAccel.y)

    def count_lap_flag(self) -> int:
        return self._s.rf2ScorVeh().mCountLapFlag

    def front_ride_height(self) -> float:
        """Altura ao solo dianteira (metros)."""
        return _safe(self._s.rf2TeleVeh().mFrontRideHeight)

    def rear_ride_height(self) -> float:
        """Altura ao solo traseira (metros)."""
        return _safe(self._s.rf2TeleVeh().mRearRideHeight)

    def drag(self) -> float:
        """Arrasto aerodinâmico (Newtons)."""
        return _safe(self._s.rf2TeleVeh().mDrag)

    def rear_brake_bias(self) -> float:
        """Balanço de freio traseiro (fração)."""
        return _safe(self._s.rf2TeleVeh().mRearBrakeBias)

    def engine_torque(self) -> float:
        """Torque do motor (Nm)."""
        return _safe(self._s.rf2TeleVeh().mEngineTorque)

    def overheating(self) -> bool:
        """Se o motor está superaquecendo."""
        return bool(self._s.rf2TeleVeh().mOverheating)

    def fuel_capacity(self) -> float:
        """Capacidade do tanque de combustível (litros)."""
        return _safe(self._s.rf2TeleVeh().mFuelCapacity)


class SMTyre:
    """Proxy de pneus sobre RF2Info."""

    def __init__(self, shmm: RF2Info):
        self._s = shmm

    def surface_temperature_ico(self) -> tuple[float, ...]:
        """Inner, Center, Outer × 4 rodas = 12 valores (°C)."""
        wheels = self._s.rf2TeleVeh().mWheels
        temps = []
        for i in range(4):
            for j in range(3):
                temps.append(_safe(wheels[i].mTemperature[j]) - 273.15)
        return tuple(temps)

    def pressure(self) -> tuple[float, ...]:
        wheels = self._s.rf2TeleVeh().mWheels
        return tuple(_safe(wheels[i].mPressure) for i in range(4))

    def wear(self) -> tuple[float, ...]:
        wheels = self._s.rf2TeleVeh().mWheels
        return tuple(_safe(wheels[i].mWear) for i in range(4))

    def load(self) -> tuple[float, ...]:
        wheels = self._s.rf2TeleVeh().mWheels
        return tuple(_safe(wheels[i].mTireLoad) for i in range(4))

    def grip(self) -> tuple[float, ...]:
        """Fração de grip (0.0-1.0) × 4 rodas."""
        wheels = self._s.rf2TeleVeh().mWheels
        return tuple(_safe(wheels[i].mGripFract) for i in range(4))

    def lateral_force(self) -> tuple[float, ...]:
        """Força lateral (Newtons) × 4 rodas."""
        wheels = self._s.rf2TeleVeh().mWheels
        return tuple(_safe(wheels[i].mLateralForce) for i in range(4))

    def suspension_deflection(self) -> tuple[float, ...]:
        """Deflexão da suspensão (metros) × 4 rodas."""
        wheels = self._s.rf2TeleVeh().mWheels
        return tuple(_safe(wheels[i].mSuspensionDeflection) for i in range(4))

    def camber(self) -> tuple[float, ...]:
        """Camber (radianos) × 4 rodas."""
        wheels = self._s.rf2TeleVeh().mWheels
        return tuple(_safe(wheels[i].mCamber) for i in range(4))

    def toe(self) -> tuple[float, ...]:
        """Toe (radianos) × 4 rodas."""
        wheels = self._s.rf2TeleVeh().mWheels
        return tuple(_safe(wheels[i].mToe) for i in range(4))


class SMBrake:
    """Proxy de freios sobre RF2Info."""

    def __init__(self, shmm: RF2Info):
        self._s = shmm

    def temperature(self) -> tuple[float, ...]:
        wheels = self._s.rf2TeleVeh().mWheels
        return tuple(_safe(wheels[i].mBrakeTemp) - 273.15 for i in range(4))


class SMEngine:
    """Proxy de motor sobre RF2Info."""

    def __init__(self, shmm: RF2Info):
        self._s = shmm

    def gear(self) -> int:
        return self._s.rf2TeleVeh().mGear

    def rpm(self) -> float:
        return _safe(self._s.rf2TeleVeh().mEngineRPM)


class SMTiming:
    """Proxy de timing sobre RF2Info."""

    def __init__(self, shmm: RF2Info):
        self._s = shmm

    def current_laptime(self) -> float:
        tv = self._s.rf2TeleVeh()
        return _safe(tv.mElapsedTime - tv.mLapStartET)

    def last_laptime(self) -> float:
        return _safe(self._s.rf2ScorVeh().mLastLapTime)

    def best_laptime(self) -> float:
        return _safe(self._s.rf2ScorVeh().mBestLapTime)

    def last_sector1(self) -> float:
        return _safe(self._s.rf2ScorVeh().mLastSector1)

    def last_sector2(self) -> float:
        return _safe(self._s.rf2ScorVeh().mLastSector2)


class SMLap:
    """Proxy de volta sobre RF2Info."""

    def __init__(self, shmm: RF2Info):
        self._s = shmm

    def number(self) -> int:
        return self._s.rf2TeleVeh().mLapNumber


def create_adapters(shmm: RF2Info):
    """Cria todos os adaptadores a partir de uma instância RF2Info.

    Returns:
        (session, vehicle, tyre, brake, engine, timing, lap)
    """
    return (
        SMSession(shmm),
        SMVehicle(shmm),
        SMTyre(shmm),
        SMBrake(shmm),
        SMEngine(shmm),
        SMTiming(shmm),
        SMLap(shmm),
    )
