CREATE DATABASE IF NOT EXISTS bookmall
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;
USE bookmall;

CREATE TABLE books (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  title        VARCHAR(200) NOT NULL,
  author       VARCHAR(100) NOT NULL,
  publisher    VARCHAR(100),
  category     VARCHAR(50),         -- 编程/算法/前端/数据库/架构/计算机基础/其他
  level        VARCHAR(20),         -- 入门 / 进阶 / 实战
  rating       DECIMAL(2,1) DEFAULT 0,   -- 评分 0-9.9
  list_price   DECIMAL(10,2) NOT NULL,   -- 标价（各平台售价围绕它）
  description  TEXT,
  tags         VARCHAR(200),        -- "Java,Spring,微服务"
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_category (category),
  INDEX idx_level (level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE book_prices (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  book_id    INT NOT NULL,
  platform   VARCHAR(50) NOT NULL,   -- 京东 / 当当 / 淘宝
  price      DECIMAL(10,2) NOT NULL,
  FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
  INDEX idx_book (book_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE inventory (
  id       INT AUTO_INCREMENT PRIMARY KEY,
  book_id  INT NOT NULL UNIQUE,
  stock    INT NOT NULL DEFAULT 0,
  FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci

CREATE TABLE reviews (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  book_id     INT NOT NULL,
  user_name   VARCHAR(50),
  rating      DECIMAL(2,1),
  content     TEXT,
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
  INDEX idx_book (book_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE coupons (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(100) NOT NULL,
  type       VARCHAR(20) NOT NULL,     -- 满减 / 折扣
  threshold  DECIMAL(10,2) NOT NULL,   -- 使用门槛
  discount   DECIMAL(10,2) NOT NULL,   -- 满减为金额，折扣为比例(0.90)
  expire     DATE NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE users (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(50) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cart_items (
  id        INT AUTO_INCREMENT PRIMARY KEY,
  user_id   INT NOT NULL,
  book_id   INT NOT NULL,
  qty       INT NOT NULL DEFAULT 1,
  added_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
  UNIQUE KEY uk_user_book (user_id, book_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE orders (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  user_id        INT NOT NULL,
  original_total DECIMAL(10,2) NOT NULL,
  total          DECIMAL(10,2) NOT NULL,     -- 优惠后总价
  coupon_id      INT NULL,
  status         VARCHAR(20) NOT NULL DEFAULT '待支付',  -- 待支付/已支付/已发货/已签收
  created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (coupon_id) REFERENCES coupons(id),
  INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE order_items (
  id        INT AUTO_INCREMENT PRIMARY KEY,
  order_id  INT NOT NULL,
  book_id   INT NOT NULL,
  price     DECIMAL(10,2) NOT NULL,
  qty       INT NOT NULL DEFAULT 1,
  FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
  FOREIGN KEY (book_id) REFERENCES books(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE logistics (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  order_id   INT NOT NULL,
  node       VARCHAR(50) NOT NULL,      -- 已揽收 / 运输中 / 派送中 / 已签收
  description VARCHAR(200),
  time       DATETIME NOT NULL,
  FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO users (name) VALUES ('测试用户');

INSERT INTO books (title, author, publisher, category, level, rating, list_price, description, tags) VALUES
-- Java
('Java核心技术 卷I：基础知识（第12版）','Cay S. Horstmann','机械工业出版社','编程','入门',4.7,149.00,'Java经典入门教材，覆盖Java SE核心语法与API。','Java,基础,入门'),
('Java编程思想（第4版）','Bruce Eckel','机械工业出版社','编程','进阶',4.5,108.00,'深入讲解Java面向对象思想与语言特性。','Java,面向对象,进阶'),
('Effective Java（第3版）','Joshua Bloch','机械工业出版社','编程','进阶',4.8,119.00,'Java最佳实践与设计规范。','Java,最佳实践'),
('Head First Java（第3版）','Kathy Sierra','中国电力出版社','编程','入门',4.4,128.00,'图文并茂的Java入门读物。','Java,入门,趣味'),
('Java并发编程实战','Brian Goetz','机械工业出版社','编程','进阶',4.6,79.00,'Java多线程与并发编程权威指南。','Java,并发,多线程'),
('深入理解Java虚拟机（第3版）','周志明','机械工业出版社','编程','进阶',4.9,129.00,'JVM原理、内存模型、垃圾回收与性能调优。','Java,JVM,进阶'),
('Java性能权威指南','Scott Oaks','人民邮电出版社','编程','进阶',4.3,89.00,'Java应用性能优化实战。','Java,性能,优化'),
('疯狂Java讲义（第5版）','李刚','电子工业出版社','编程','入门',4.2,139.00,'体系完整的Java学习教程。','Java,入门,教程'),
-- Spring
('Spring Boot实战','Craig Walls','人民邮电出版社','编程','实战',4.4,69.00,'Spring Boot快速入门与项目实战。','Spring,Java,实战'),
('深入浅出Spring Boot 2.x','杨开振','人民邮电出版社','编程','实战',4.5,99.00,'Spring Boot开发全流程案例讲解。','Spring,Java,实战'),
('Spring实战（第5版）','Craig Walls','人民邮电出版社','编程','实战',4.6,89.00,'Spring框架系统学习与实战。','Spring,Java,框架'),
('Spring Cloud微服务实战','翟永超','电子工业出版社','编程','实战',4.3,79.00,'Spring Cloud微服务开发指南。','Spring,微服务,实战'),
('Spring Boot编程思想','小马哥','电子工业出版社','编程','进阶',4.7,128.00,'深入解析Spring Boot自动配置原理。','Spring,原理,进阶'),
('精通Spring 4.x','陈雄华','电子工业出版社','编程','进阶',4.1,128.00,'Spring框架源码与实战应用。','Spring,Java,源码'),
-- Python
('Python编程：从入门到实践（第3版）','Eric Matthes','人民邮电出版社','编程','入门',4.8,109.00,'Python零基础入门经典。','Python,入门'),
('流畅的Python（第2版）','Luciano Ramalho','人民邮电出版社','编程','进阶',4.7,139.00,'深入Python语言特性与惯用法。','Python,进阶,语言'),
('Python核心编程（第3版）','Wesley Chun','人民邮电出版社','编程','入门',4.2,99.00,'Python基础与进阶知识体系。','Python,基础'),
('Python深度学习（第2版）','François Chollet','人民邮电出版社','AI','进阶',4.6,129.00,'Keras作者讲解深度学习实战。','Python,深度学习,AI'),
('Python数据科学手册','Jake VanderPlas','人民邮电出版社','数据','进阶',4.5,109.00,'NumPy/Pandas/Matplotlib数据科学工具。','Python,数据分析'),
-- 算法
('算法导论（第3版）','Thomas H. Cormen','机械工业出版社','算法','进阶',4.7,128.00,'算法理论与设计的经典教材。','算法,理论,进阶'),
('算法（第4版）','Robert Sedgewick','人民邮电出版社','算法','进阶',4.8,99.00,'用Java讲解经典算法与数据结构。','算法,Java,数据结构'),
('剑指Offer（第2版）','何海涛','电子工业出版社','算法','实战',4.5,79.00,'面试算法题系统训练。','算法,面试,刷题'),
('labuladong的算法小抄','付东来','电子工业出版社','算法','实战',4.6,99.00,'算法套路模板与刷题路线。','算法,刷题,实战'),
('大话数据结构','程杰','清华大学出版社','算法','入门',4.3,59.00,'通俗易懂的数据结构入门。','数据结构,入门'),
-- 前端
('JavaScript高级程序设计（第4版）','Matt Frisbie','人民邮电出版社','前端','进阶',4.8,129.00,'JS进阶必读，涵盖ES6+新特性。','JavaScript,前端,进阶'),
('你不知道的JavaScript（上卷）','Kyle Simpson','人民邮电出版社','前端','进阶',4.6,59.00,'深入JS作用域与闭包。','JavaScript,进阶'),
('Vue.js设计与实现','霍春阳','人民邮电出版社','前端','进阶',4.9,89.00,'Vue3响应式原理与源码解析。','Vue,前端,源码'),
('深入浅出Vue.js','刘博文','人民邮电出版社','前端','进阶',4.5,79.00,'Vue.js原理与实现分析。','Vue,源码,进阶'),
('CSS世界','张鑫旭','人民邮电出版社','前端','进阶',4.4,69.00,'CSS布局与渲染原理。','CSS,前端'),
-- 数据库
('MySQL技术内幕：InnoDB存储引擎（第2版）','姜承尧','机械工业出版社','数据库','进阶',4.7,99.00,'InnoDB存储引擎原理深度讲解。','MySQL,数据库,原理'),
('高性能MySQL（第3版）','Baron Schwartz','电子工业出版社','数据库','进阶',4.8,128.00,'MySQL性能优化与架构设计。','MySQL,优化,数据库'),
('Redis设计与实现','黄健宏','机械工业出版社','数据库','进阶',4.7,79.00,'Redis源码与内部实现原理。','Redis,缓存,进阶'),
('数据库系统概念（第7版）','Abraham Silberschatz','机械工业出版社','数据库','入门',4.6,99.00,'数据库系统理论经典教材。','数据库,理论,入门'),
-- 架构设计
('设计模式：可复用面向对象软件的基础','Erich Gamma','机械工业出版社','架构','进阶',4.6,59.00,'GoF二十三种经典设计模式。','设计模式,面向对象,架构'),
('代码整洁之道','Robert C. Martin','人民邮电出版社','架构','进阶',4.7,59.00,'编写高质量可维护代码的原则。','代码质量,重构'),
('重构：改善既有代码的设计（第2版）','Martin Fowler','人民邮电出版社','架构','进阶',4.8,118.00,'重构方法论与实战案例。','重构,代码质量,架构'),
('深入理解计算机系统（第3版）','Randal E. Bryant','机械工业出版社','计算机基础','进阶',4.9,139.00,'CSAPP，从程序员视角理解计算机系统。','计算机系统,底层'),
('领域驱动设计','Eric Evans','人民邮电出版社','架构','进阶',4.5,79.00,'DDD领域建模方法论。','DDD,架构,设计'),
-- 微服务/分布式
('微服务架构设计模式','Chris Richardson','机械工业出版社','架构','进阶',4.6,99.00,'微服务拆分、通信、数据一致性模式。','微服务,架构,模式'),
('凤凰架构','周志明','机械工业出版社','架构','进阶',4.8,99.00,'构建可靠大型分布式系统。','架构,分布式,进阶'),
('分布式系统原理与范型','Andrew S. Tanenbaum','清华大学出版社','架构','进阶',4.4,69.00,'分布式系统理论与经典算法。','分布式,理论'),
('深入理解分布式系统','唐阳','机械工业出版社','架构','进阶',4.5,89.00,'分布式一致性、容错与实战。','分布式,实战'),
-- 计算机基础
('计算机网络：自顶向下方法（第7版）','James F. Kurose','机械工业出版社','计算机基础','入门',4.8,89.00,'从应用层到物理层的网络经典教材。','网络,基础,HTTP'),
('操作系统导论','Remzi H. Arpaci-Dusseau','人民邮电出版社','计算机基础','入门',4.7,99.00,'OS三大主题：虚拟化、并发、持久化。','操作系统,基础'),
('图解HTTP','上野宣','人民邮电出版社','计算机基础','入门',4.3,49.00,'HTTP协议图解入门。','HTTP,网络,入门'),
('程序员的自我修养','俞甲子','电子工业出版社','计算机基础','进阶',4.6,65.00,'编译、链接与库的底层原理。','编译,链接,底层'),
-- 其他
('黑客与画家','Paul Graham','人民邮电出版社','其他','入门',4.5,49.00,'编程文化与创业随笔。','编程文化,随笔'),
('程序员修炼之道（第2版）','David Thomas','电子工业出版社','其他','入门',4.6,79.00,'从程序员到专业人士的成长指南。','职业发展,编程'),
('人月神话','Frederick P. Brooks','清华大学出版社','其他','进阶',4.4,49.00,'软件工程管理的经典。','软件工程,管理'),
('数学之美（第3版）','吴军','人民邮电出版社','其他','入门',4.7,69.00,'用数学解决工程问题的科普读物。','数学,算法,科普');

INSERT INTO book_prices (book_id, platform, price) SELECT id, '京东', ROUND(list_price * 0.85, 2) FROM books;
INSERT INTO book_prices (book_id, platform, price) SELECT id, '当当', ROUND(list_price * 0.88, 2) FROM books;
INSERT INTO book_prices (book_id, platform, price) SELECT id, '淘宝', ROUND(list_price * 0.82, 2) FROM books;

INSERT INTO inventory (book_id, stock) SELECT id, (id * 7 + 13) % 100 FROM books;
UPDATE inventory SET stock = 0 WHERE book_id IN (3, 15, 27);

INSERT INTO reviews (book_id, user_name, rating, content) VALUES
(1,'张三',5.0,'讲解非常细致，代码示例丰富，适合Java零基础入门。'),
(1,'李四',4.0,'内容经典，但部分API章节略显过时，需结合新版文档看。'),
(1,'王五',4.5,'作为入门书很扎实，练习项目也很实用。'),
(9,'张三',4.5,'Spring Boot实战入门首选，案例完整。'),
(9,'赵六',3.5,'讲解偏浅，进阶内容不足，适合快速上手不适合深入。'),
(9,'孙七',5.0,'跟着做完项目就能干活了，非常推荐。'),
(6,'李四',5.0,'JVM神书，国内程序员必读，深入浅出。'),
(6,'赵六',4.5,'垃圾回收和内存模型讲得极清楚，面试必备。'),
(6,'王五',4.0,'有点难，需要有Java基础再看。'),
(27,'张三',5.0,'Vue3源码级讲解，霍春阳老师功力深厚。'),
(27,'孙七',4.5,'响应式原理讲得很透，但需要有JS基础。'),
(27,'李四',4.0,'偏原理，实战部分较少。'),
(20,'赵六',4.5,'算法圣经，理论性强，适合系统学习。'),
(20,'王五',3.5,'数学证明偏多，工程实践略少，需搭配其他书。'),
(20,'孙七',5.0,'配合MIT公开课看效果最佳。');

INSERT INTO reviews (book_id, user_name, rating, content)
SELECT id, '书友A', 5.0, '内容详实，讲解清晰，强烈推荐。' FROM books WHERE id NOT IN (1,6,9,20,27);
INSERT INTO reviews (book_id, user_name, rating, content)
SELECT id, '书友B', 3.5, '整体不错，但部分章节略显啰嗦，可以跳读。' FROM books WHERE id NOT IN (1,6,9,20,27);
INSERT INTO reviews (book_id, user_name, rating, content)
SELECT id, '书友C', 4.0, '书不错，配套代码有点旧，需要自己调试。' FROM books WHERE id NOT IN (1,6,9,20,27);

INSERT INTO coupons (name, type, threshold, discount, expire) VALUES
('满100减20','满减',100.00,20.00,'2026-12-31'),
('满200减50','满减',200.00,50.00,'2026-12-31'),
('满300减80','满减',300.00,80.00,'2026-12-31'),
('满50减10','满减',50.00,10.00,'2026-12-31'),
('满150减30','满减',150.00,30.00,'2026-12-31'),
('新人满80减15','满减',80.00,15.00,'2026-12-31'),
('全场9折','折扣',0.00,0.90,'2026-12-31'),
('全场95折','折扣',0.00,0.95,'2026-12-31');
