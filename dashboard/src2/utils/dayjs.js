import dayjs from 'dayjs/esm';
import relativeTime from 'dayjs/esm/plugin/relativeTime';
import localizedFormat from 'dayjs/esm/plugin/localizedFormat';
import updateLocale from 'dayjs/esm/plugin/updateLocale';
import isToday from 'dayjs/esm/plugin/isToday';
import duration from 'dayjs/esm/plugin/duration';

dayjs.extend(updateLocale);
dayjs.extend(relativeTime);
dayjs.extend(localizedFormat);
dayjs.extend(isToday);
dayjs.extend(duration);

export default dayjs;
