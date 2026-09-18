from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import uuid


class CompanyConfigError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Company:
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class CompanyConfig:
    companies: tuple[Company, ...] = ()
    selected_company_id: str | None = None


class CompanyConfigRepository:
    SCHEMA_VERSION = 1

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> CompanyConfig:
        if not self.path.exists():
            return CompanyConfig()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return self._decode(payload)
        except (OSError, json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
            if isinstance(exc, CompanyConfigError):
                raise
            raise CompanyConfigError(f"No se pudo leer la configuración de empresas: {exc}") from exc

    def add(self, name: str) -> CompanyConfig:
        clean_name = self._clean_name(name)
        config = self.load()
        self._ensure_unique_name(config, clean_name)
        company = Company(uuid.uuid4().hex, clean_name)
        updated = CompanyConfig(
            companies=(*config.companies, company),
            selected_company_id=config.selected_company_id or company.id,
        )
        self._save(updated)
        return updated

    def rename(self, company_id: str, name: str) -> CompanyConfig:
        clean_name = self._clean_name(name)
        config = self.load()
        self._ensure_unique_name(config, clean_name, excluding_id=company_id)
        found = False
        companies: list[Company] = []
        for company in config.companies:
            if company.id == company_id:
                companies.append(Company(company.id, clean_name))
                found = True
            else:
                companies.append(company)
        if not found:
            raise ValueError("La empresa seleccionada no existe")
        updated = CompanyConfig(tuple(companies), config.selected_company_id)
        self._save(updated)
        return updated

    def select(self, company_id: str) -> CompanyConfig:
        config = self.load()
        if not any(company.id == company_id for company in config.companies):
            raise ValueError("La empresa seleccionada no existe")
        updated = CompanyConfig(config.companies, company_id)
        self._save(updated)
        return updated

    @staticmethod
    def _clean_name(name: str) -> str:
        clean_name = " ".join(str(name).split())
        if not clean_name:
            raise ValueError("Ingresá un nombre para la empresa")
        if len(clean_name) > 80:
            raise ValueError("El nombre de la empresa no puede superar 80 caracteres")
        return clean_name

    @staticmethod
    def _ensure_unique_name(config: CompanyConfig, name: str, excluding_id: str | None = None) -> None:
        normalized = name.casefold()
        if any(company.id != excluding_id and company.name.casefold() == normalized for company in config.companies):
            raise ValueError("Ya existe una empresa con ese nombre")

    def _decode(self, payload: object) -> CompanyConfig:
        if not isinstance(payload, dict) or payload.get("schema_version") != self.SCHEMA_VERSION:
            raise CompanyConfigError("La configuración de empresas no tiene un formato compatible")
        raw_companies = payload.get("companies")
        selected = payload.get("selected_company_id")
        if not isinstance(raw_companies, list) or (selected is not None and not isinstance(selected, str)):
            raise CompanyConfigError("La configuración de empresas está incompleta")
        companies: list[Company] = []
        seen_ids: set[str] = set()
        seen_names: set[str] = set()
        for item in raw_companies:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not isinstance(item.get("name"), str):
                raise CompanyConfigError("La configuración contiene una empresa inválida")
            company_id = item["id"]
            name = self._clean_name(item["name"])
            if company_id in seen_ids or name.casefold() in seen_names:
                raise CompanyConfigError("La configuración contiene empresas duplicadas")
            seen_ids.add(company_id)
            seen_names.add(name.casefold())
            companies.append(Company(company_id, name))
        if selected is not None and selected not in seen_ids:
            raise CompanyConfigError("La empresa seleccionada no existe en la configuración")
        return CompanyConfig(tuple(companies), selected)

    def _save(self, config: CompanyConfig) -> None:
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "companies": [{"id": company.id, "name": company.name} for company in config.companies],
            "selected_company_id": config.selected_company_id,
        }
        temporary = self.path.with_name(f"{self.path.name}.tmp")
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except OSError:
            temporary.unlink(missing_ok=True)
            raise
