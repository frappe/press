import { bytes } from '../../utils/format';

function getUnit(value, seriesName) {
	if (seriesName === 'bytes') return bytes(value);
	else return `${+value.toFixed(2)} ${seriesName}`;
}

export { getUnit };
