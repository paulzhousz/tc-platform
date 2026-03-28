import { buildSqlFromVisual } from "./buildCreateTableSql";
import {
  applySubColumns,
  visualPresetMasterSub,
  visualPresetSingle,
} from "./createTableVisualPresets";

/** 与「表结构」单表模板一致的 SQL（便于两种模式对齐） */
export function getExampleFromPresetSingle(dialect: "mysql" | "postgres"): string {
  return buildSqlFromVisual(visualPresetSingle(dialect));
}

/** 与「表结构」主子表模板一致的 SQL */
export function getExampleFromPresetMasterSub(dialect: "mysql" | "postgres"): string {
  return buildSqlFromVisual(applySubColumns(visualPresetMasterSub(dialect)));
}

/** 旧版 MySQL 示例（含 sys_user 外键，需库中存在 sys_user） */
export const LEGACY_MYSQL_WITH_USER_FK = `-- MySQL 旧版示例（依赖 sys_user 表）
CREATE TABLE \`gen_demo01\` (
  \`name\` varchar(64) DEFAULT NULL COMMENT '名称',
  \`id\` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  \`uuid\` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  \`status\` varchar(10) NOT NULL COMMENT '是否启用(0:启用 1:禁用)',
  \`description\` text COMMENT '备注/描述',
  \`created_time\` datetime NOT NULL COMMENT '创建时间',
  \`updated_time\` datetime NOT NULL COMMENT '更新时间',
  \`created_id\` int DEFAULT NULL COMMENT '创建人ID',
  \`updated_id\` int DEFAULT NULL COMMENT '更新人ID',
  PRIMARY KEY (\`id\`),
  UNIQUE KEY \`uuid\` (\`uuid\`),
  KEY \`ix_gen_demo01_created_id\` (\`created_id\`),
  KEY \`ix_gen_demo01_updated_id\` (\`updated_id\`),
  CONSTRAINT \`gen_demo01_ibfk_1\` FOREIGN KEY (\`created_id\`) REFERENCES \`sys_user\` (\`id\`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT \`gen_demo01_ibfk_2\` FOREIGN KEY (\`updated_id\`) REFERENCES \`sys_user\` (\`id\`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='示例表'`;

/** 旧版 PostgreSQL 示例（含 sys_user 外键） */
export const LEGACY_POSTGRES_WITH_USER_FK = `-- PostgreSQL 旧版示例（依赖 sys_user 表）
CREATE TABLE gen_demo01(
  id SERIAL NOT NULL,
  uuid varchar(64) NOT NULL,
  name varchar(64),
  status varchar(10) NOT NULL,
  description text,
  created_time timestamp without time zone NOT NULL,
  updated_time timestamp without time zone NOT NULL,
  created_id integer,
  updated_id integer,
  PRIMARY KEY(id),
  CONSTRAINT gen_demo01_created_id_fkey FOREIGN key(created_id) REFERENCES sys_user(id),
  CONSTRAINT gen_demo01_updated_id_fkey FOREIGN key(updated_id) REFERENCES sys_user(id)
);
CREATE UNIQUE INDEX en_demo01_uuid_key ON public.gen_demo01 USING btree (uuid);
CREATE INDEX ix_gen_demo01_created_id ON public.gen_demo01 USING btree (created_id);
CREATE INDEX ix_gen_demo01_updated_id ON public.gen_demo01 USING btree (updated_id);
COMMENT ON TABLE gen_demo01 IS '示例表';
COMMENT ON COLUMN gen_demo01.name IS '名称';
COMMENT ON COLUMN gen_demo01.id IS '主键ID';
COMMENT ON COLUMN gen_demo01.uuid IS 'UUID全局唯一标识';
COMMENT ON COLUMN gen_demo01.status IS '是否启用(0:启用 1:禁用)';
COMMENT ON COLUMN gen_demo01.description IS '备注/描述';
COMMENT ON COLUMN gen_demo01.created_time IS '创建时间';
COMMENT ON COLUMN gen_demo01.updated_time IS '更新时间';
COMMENT ON COLUMN gen_demo01.created_id IS '创建人ID';
COMMENT ON COLUMN gen_demo01.updated_id IS '更新人ID';`;
