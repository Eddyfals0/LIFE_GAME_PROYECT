# Índice

- Introducción
- Arquitectura del Sistema
- Entorno y Recursos
- Funcionamiento de los Agentes
- Red Neuronal y Aprendizaje Reforzado
- Persistencia de Datos
- Conclusiones

## Introducción

Este proyecto simula **16 mundos independientes en simultáneo** en una sola pantalla, cada uno con agentes inteligentes que deben sobrevivir. Cada mundo es un entorno cerrado con recursos como arbustos (alimento) y lagos (agua), donde los agentes ven reducidos sus niveles de hambre y sed con el tiempo. El objetivo es que los agentes aprendan a maximizar su tiempo de supervivencia mediante el **aprendizaje reforzado**. En la práctica, cada agente percibe el entorno inmediato y sus estados internos (hambre, sed, etc.) para decidir acciones que le permitan acercarse a los recursos. El sistema registra continuamente la duración de vida de cada agente, guardando la red neuronal (“cerebro”) del mejor cuando se supera el récord de supervivencia.

 

El aprendizaje reforzado (RL) es un paradigma del aprendizaje automático donde un agente aprende por **ensayo y error** a tomar decisiones que maximicen una recompensa acumulada[es.wikipedia.org](https://es.wikipedia.org/wiki/Aprendizaje_por_refuerzo#:~:text=reinforcement learning,El problema%2C por su). En este contexto, el agente ejecuta acciones en su entorno, recibe retroalimentación (recompensas) según el resultado, y ajusta su política de acción para reforzar las conductas que llevan a mejores resultados[aws.amazon.com](https://aws.amazon.com/es/what-is/reinforcement-learning/#:~:text=Imita el proceso de aprendizaje,apartan del objetivo se ignoran). En este sistema, los agentes usan una red neuronal simple como política, entrenada con el algoritmo REINFORCE, que optimiza las acciones con base en las recompensas obtenidas.

## Arquitectura del Sistema

El sistema se organiza en varios componentes principales que colaboran para simular los mundos y entrenar a los agentes:

- **Gestor de simulación (Controlador principal):** Coordina el ciclo de actualizaciones de los 16 mundos, procesando cada paso de simulación en paralelo. Administra la creación inicial de cada mundo, el reinicio de mundos que pierden todos los agentes y el seguimiento del mejor desempeño global.
- **Mundos simulados:** Cada mundo es una instancia autónoma que incluye su propio conjunto de agentes y recursos. Internamente, el mundo puede representarse como una cuadrícula o espacio 2D con posiciones para arbustos, lagos y agentes. Cada mundo se actualiza de forma independiente, aunque bajo el mismo bucle global.
- **Agentes:** Son entidades autónomas con sensores y actuadores. Tienen atributos internos (niveles de hambre, sed, felicidad, miedo, memoria corta) y un “cerebro” constituido por una red neuronal. En cada paso, un agente recibe información del mundo (visión local y estados internos), decide una acción con su red neuronal y luego actúa (por ejemplo, moverse o consumir un recurso).
- **Red neuronal (modelo del agente):** Cada agente utiliza una red neuronal simple (por ejemplo, un perceptrón multicapa) que procesa sus observaciones y produce una distribución de probabilidad sobre las acciones posibles. Esta red se entrena con aprendizaje reforzado.
- **Persistencia y registro:** Existen módulos responsables de guardar el progreso del entrenamiento. Esto incluye mantener el **récord de supervivencia** (mejor tiempo de vida de un agente) y serializar la red neuronal asociada cuando se supera dicho récord. También se almacenan métricas como el tiempo total de entrenamiento y el número de mundos creados para poder reanudar el proceso tras cerrar el programa.

Cada uno de estos componentes colabora para que los agentes mejoren con el tiempo. El resultado es un sistema modular donde se integran la simulación del entorno, la lógica de los agentes y el aprendizaje automático.

## Entorno y Recursos

Cada uno de los 16 mundos simulados incluye los siguientes elementos clave en el entorno:

- **Recursos:**
  - *Arbustos (celdas verdes):* Objetos que los agentes pueden consumir para reponer energía alimenticia. Cuando un agente interactúa (se mueve sobre) con un arbusto, su nivel de **hambre** se restaura parcialmente o por completo.
  - *Lagos (celdas azul claro):* Fuentes de agua. De forma análoga, cuando el agente accede a un lago, su nivel de **sed** disminuye.
- **Estados internos:** Los agentes poseen dos indicadores principales que deben gestionar:
  - *Hambre:* Disminuye con el tiempo. Si llega a cero, el agente muere.
  - *Sed:* Funciona igual que el hambre, pero relacionado con el agua. Debe mantenerse por encima de cero para sobrevivir.
- **Recarga de recursos:** Al consumir un recurso (arbusto o lago), el nivel interno correspondiente del agente aumenta. Los recursos pueden tener regeneración o ser de un solo uso, según la implementación, incentivando a los agentes a planificar rutas de recolección.
- **Inicio y reinicio de mundos:** Cada mundo comienza con un conjunto de agentes y recursos distribuidos en el espacio. Si en algún momento todos los agentes de un mundo mueren (por hambre, sed u otras causas), ese mundo se **reinicia**: se vuelve a crear una nueva instancia (contando en el registro de mundos creados) con agentes frescos, permitiendo continuar el entrenamiento sin detener el sistema.
- **Entorno paralelo:** Los 16 mundos corren simultáneamente, lo que enriquece la diversidad de experiencias de los agentes y acelera el aprendizaje global, ya que a cada paso se generan múltiples trayectorias de agentes.

Este entorno dinámico plantea un desafío de supervivencia, en el que los agentes deben explorar el espacio, encontrar recursos y gestionar sus niveles internos para maximizar su tiempo de vida.

## Funcionamiento de los Agentes

Cada agente en la simulación opera siguiendo un ciclo simple de percepción-acción, alimentado por su red neuronal y sus estados internos. Sus características principales son:

- **Visión Local:** El agente percibe su entorno inmediato. Por ejemplo, podría capturar información de una región cuadrada alrededor de su posición (una “ventana de visión”), indicando la presencia de arbustos, lagos o límites del mundo en casillas cercanas. Esta visión se codifica en un vector de entrada.
- **Estados Internos:** Además de la visión, el agente monitorea sus niveles de hambre y sed, así como dos valores emocionales llamados *felicidad* y *miedo*. La *felicidad* puede incrementarse al alcanzar objetivos positivos (como comer), mientras que el *miedo* aumenta si la situación es precaria (por ejemplo, acercarse al nivel cero de hambre). Estos valores emocionales sirven como métricas internas adicionales y se proveen también como entradas a la red neuronal.
- **Memoria de corto plazo:** Los agentes mantienen una memoria breve de observaciones pasadas, que puede consistir en los últimos pasos o percepciones. Esta memoria se actualiza en cada ciclo y se incluye junto con la percepción actual para que la red neuronal tenga contexto histórico. Gracias a ello, el agente puede, por ejemplo, recordar la ubicación reciente de un recurso o la dirección hacia la que se movió.
- **Toma de Decisiones y Acciones:** La red neuronal del agente procesa el vector de entrada (visión local + estados internos + memoria) y produce una salida que representa una probabilidad para cada acción posible (por ejemplo, moverse hacia arriba/abajo/izquierda/derecha, quedarse quieto, etc.). Se elige una acción (por lo general muestreándola de esa distribución) y el agente la ejecuta sobre el entorno. Por ejemplo, moverse a una casilla vecina o consumir un recurso adyacente.
- **Actualización de Estados:** Tras actuar, los niveles internos (hambre y sed) se decrementan. Si el agente consumió un arbusto, su hambre se restaura; si bebió en un lago, su sed aumenta. Las emociones también se ajustan: comerse un arbusto podría incrementar la felicidad, y aproximarse peligrosamente a no comer por mucho tiempo podría aumentar el miedo.
- **Ciclo de Simulación:** Este proceso (percepción → decisión → acción → actualización) ocurre en cada paso de tiempo discreto de la simulación. Si en algún momento el hambre o la sed del agente llega a cero, el agente muere y desaparece del mundo.
- **Interacción con Otros Agentes:** Si hay múltiples agentes en el mismo mundo, compiten por los mismos recursos. La visión local también puede incluir la posición de otros agentes. La necesidad de recursos y el enfoque en supervivencia implican que los agentes deben adaptarse tanto a los recursos disponibles como a la presencia de otros agentes.

En resumen, cada agente percibe su entorno inmediato y sus propias necesidades internas, las combina a través de su cerebro (red neuronal) y ejecuta acciones para sobrevivir. La memoria de corto plazo y los estados emocionales agregan complejidad a la percepción, permitiendo que las decisiones tengan en cuenta el historial reciente y motivaciones internas sencillas.

## Red Neuronal y Aprendizaje Reforzado

La **red neuronal** es el núcleo de la inteligencia de cada agente. Su diseño se caracteriza por lo siguiente:

- **Arquitectura:** Es una red neuronal simple (por ejemplo, una red feedforward de una o dos capas ocultas). La entrada de la red incluye el vector de visión local del agente, sus niveles de hambre y sed, los valores de felicidad y miedo, y la memoria reciente. La salida de la red es un conjunto de probabilidades (normalizadas con softmax) correspondientes a las acciones posibles del agente. De este modo, la red define una *política estocástica*: dadas unas observaciones, asigna una probabilidad a cada acción.
- **Función de recompensa:** Durante el entrenamiento, cada acción del agente genera una recompensa. Una estrategia común es otorgar una pequeña recompensa por cada paso que el agente permanezca vivo (incentivando la supervivencia continua) y recompensas adicionales al consumir recursos (por ejemplo, +X por comer un arbusto, +Y por beber). La suma de estas recompensas a lo largo del episodio conforma la **recompensa acumulada** que el agente intenta maximizar. En general, buscamos que los agentes maximicen la suma total de recompensas a lo largo del tiempo, lo cual equivale a sobrevivir más pasos y aprovechar recursos[aws.amazon.com](https://aws.amazon.com/es/what-is/reinforcement-learning/#:~:text=El RL se centra intrínsecamente,de inmediato para cada paso).
- **Entrenamiento con REINFORCE:** El algoritmo empleado es **REINFORCE**, un método de gradiente de política en aprendizaje reforzado. El proceso de entrenamiento es el siguiente:
  1. Se ejecuta una serie de episodios (trayectorias) en los mundos simulados, donde los agentes actúan según su política actual.
  2. Durante cada paso, el agente recolecta recompensas inmediatas en función de sus acciones y actualiza sus estados internos. Todas estas recompensas se acumulan hasta el final del episodio.
  3. Al término del episodio, el algoritmo REINFORCE actualiza los pesos de la red neuronal usando la regla del gradiente de log-probabilidad: las acciones que obtuvieron alta recompensa incrementan su probabilidad futura. En práctica, esto significa aumentar la probabilidad de las acciones que condujeron a mejores resultados y reducir la probabilidad de las que no fueron beneficiosas.
  4. Este ajuste de pesos guía la política del agente hacia comportamientos que maximizan la recompensa a largo plazo[aws.amazon.com](https://aws.amazon.com/es/what-is/reinforcement-learning/#:~:text=El RL se centra intrínsecamente,de inmediato para cada paso). En otras palabras, el agente **aprende a reforzar las acciones exitosas** y a evitar las menos útiles.
- **Actualización de la memoria:** En cada paso, además de recibir recompensas, el agente actualiza su memoria con las observaciones recientes antes de la siguiente decisión. Así, la red puede utilizar información histórica inmediata para planificar el siguiente movimiento.
- **Entrenamiento simultáneo en múltiples mundos:** Dado que hay 16 mundos paralelos, el entrenamiento recolecta experiencias de todos ellos. Esto enriquece el aprendizaje, pues los agentes enfrentan escenarios diversos en cada mundo. Las actualizaciones de la red pueden acumular gradientes de los agentes de todos los entornos antes de aplicar los cambios, acelerando el proceso de entrenamiento.

En síntesis, la red neuronal procesa la visión local y los estados internos de cada agente para producir acciones de supervivencia. El algoritmo REINFORCE ajusta esta red en base a las recompensas obtenidas, enfocándose en maximizar la supervivencia y la obtención de recursos. Como resultado, con el tiempo los agentes desarrollan comportamientos más eficientes para vivir el mayor tiempo posible.

## Persistencia de Datos

Para garantizar la continuidad del entrenamiento y preservar los resultados, el sistema implementa varios mecanismos de persistencia:

- **Guardado del mejor agente:** Se mantiene un registro del récord de supervivencia (el mayor número de pasos vividos por un agente). Cuando un agente supera este récord, se considera su red neuronal como la *mejor* hasta el momento. En ese instante, los parámetros de su red (pesos y sesgos) se serializan y guardan en un archivo. De esta forma, se almacena el “mejor cerebro” para su posterior análisis o reuso.
- **Registro de progreso:** El sistema registra métricas globales como el tiempo total de entrenamiento transcurrido (por ejemplo, en pasos de simulación o episodios completados) y el número de mundos que se han creado (reinicios de entornos). Estos datos se guardan en disco (por ejemplo, en un archivo de texto o base de datos ligera) para permitir reanudar el entrenamiento sin perder historial.
- **Continuidad al cerrar:** Al finalizar la ejecución del programa (o periódicamente), se escribe en disco toda la información relevante: estados de entrenamiento, cuentas de mundos y el último estado de los agentes si es necesario. Esto asegura que al reiniciar el programa, se pueda cargar el progreso previo y continuar desde donde se dejó.
- **Formato de almacenamiento:** Si el proyecto está implementado en un lenguaje como Python, es común usar bibliotecas de serialización (por ejemplo, `pickle` o formatos de modelos de redes neuronales) para guardar los pesos de la red. Las estadísticas y contadores se pueden almacenar en formatos legibles (JSON, CSV) para facilitar su visualización y análisis posterior.
- **Seguridad de datos:** Al mantener persistencia, se evita perder horas de entrenamiento en caso de apagones o cierres inesperados. Además, al tener guardados los mejores agentes, se puede reproducir o comparar estrategias sin volver a entrenar desde cero.

Gracias a este sistema de persistencia, el proyecto permite un entrenamiento largo y gradual de los agentes, mientras conserva el conocimiento adquirido y los hitos alcanzados a lo largo del tiempo.

## Conclusiones

Este proyecto integra elementos de simulación y aprendizaje automático para crear un entorno de entrenamiento de agentes inteligentes. La arquitectura modular (con mundos paralelos, agentes autónomos y un gestor central) facilita la experimentación y escalabilidad del sistema. Al emplear aprendizaje reforzado mediante redes neuronales, los agentes adquieren comportamientos complejos a partir de reglas simples (hambre, sed, recompensa por supervivencia). La inclusión de factores como memoria de corto plazo y estados emocionales (felicidad/miedo) añade riqueza al modelo de agente, aunque mantiene la implementación accesible para desarrolladores con conocimientos básicos de IA.

 

Entre las fortalezas del diseño destacan la capacidad de acelerar el aprendizaje al usar múltiples entornos simultáneos, y el mecanismo de persistencia que asegura no perder el progreso. El guardado del mejor agente fomenta la mejora continua, ya que cada nuevo récord amplía la base de soluciones óptimas.

 

Para futuros desarrollos, podría considerarse extender la red neuronal (por ejemplo, usando arquitecturas recurrentes más profundas) o explorar algoritmos de RL más sofisticados (como A2C o PPO) para mejorar la estabilidad del entrenamiento. Además, enriquecer el entorno con más tipos de recursos o desafíos (depredadores, variabilidad climática, etc.) haría la simulación aún más realista.

 

En conjunto, esta documentación proporciona una visión clara y completa del sistema, explicando su propósito, funcionamiento interno y las técnicas de IA utilizadas. Los principios aquí descritos son de aplicación general en simulaciones multiagente y aprendizaje reforzado, por lo que el lector con conocimientos en IA podrá adaptarlos a proyectos similares en el futuro[es.wikipedia.org](https://es.wikipedia.org/wiki/Aprendizaje_por_refuerzo#:~:text=reinforcement learning,El problema%2C por su)[aws.amazon.com](https://aws.amazon.com/es/what-is/reinforcement-learning/#:~:text=El RL se centra intrínsecamente,de inmediato para cada paso).

Citas

![Favicon](https://www.google.com/s2/favicons?domain=https://es.wikipedia.org&sz=32)

Aprendizaje por refuerzo - Wikipedia, la enciclopedia libre

https://es.wikipedia.org/wiki/Aprendizaje_por_refuerzo

![Favicon](https://www.google.com/s2/favicons?domain=https://aws.amazon.com&sz=32)

¿Qué es el Aprendizaje mediante refuerzo? - Explicación del Aprendizaje mediante refuerzo - AWS

https://aws.amazon.com/es/what-is/reinforcement-learning/

![Favicon](https://www.google.com/s2/favicons?domain=https://aws.amazon.com&sz=32)

¿Qué es el Aprendizaje mediante refuerzo? - Explicación del Aprendizaje mediante refuerzo - AWS

https://aws.amazon.com/es/what-is/reinforcement-learning/
